#!/usr/bin/env python3
"""
RDS 实例迁移工具：把现有生产库完整搬到新的 RDS PostgreSQL 实例

设计目标
--------
缩容到新实例（pg.n2e.1c.1m，1核2G/最大连接50）时，数据必须无损搬迁。人工敲
pg_dump | pg_restore 的风险在于几个静默失败点，本脚本把它们全部前移到执行之前：

1. **pgvector 是否在新实例可用** —— items.embedding 是 vector 类型，若新实例所在
   引擎版本没有 pgvector 扩展，迁移到一半才发现就没有退路了。
2. **pg_dump 客户端版本是否 ≥ 源端服务端版本** —— pg_dump 拒绝连接比它更新的服务端
   （"server version mismatch"）。宿主机自带 pg_dump 往往是 13/14，而 RDS 可能已是 18。
3. **目标端大版本 ≥ 源端** —— 反向恢复（新→旧）不受支持，所以要确保不会退不回去。
4. **目标库非空** —— 往有表的库上 restore 会造成数据混杂，默认直接中止。
5. **恢复后行数一致性** —— pg_restore 遇到错误时返回码为 1 但只打印若干 warning，
   人眼很容易漏过；这里逐表比对源/目标行数与向量覆盖率。

对源库**完全只读**（只有 SELECT 与 pg_dump），不会做任何写操作或 DDL。

用法
----
    # 在 ECS 上执行（源库走内网地址，本机才可达）
    cd /opt/shunyishang
    .venv/bin/python scripts/migrate_rds.py \\
        --dst "postgresql://<新实例账号>:<密码>@<新实例内网地址>:5432/wuxing_db"

    # 源库默认取 .env.ecs 里的 DATABASE_URL，也可显式指定
    ... --src "postgresql://..."

    # 宿主机 pg_dump 版本过旧时，借容器里的新版客户端（docker 形式必须带 -i，
    # 因为归档是靠 stdin 管道传的，避开宿主机/容器路径不一致）
    ... --pg-bin "docker exec -i wuxing-db"

    # 目标库确实需要覆盖（自建空库残留了表）时
    ... --force

安全边界
--------
- 不 DROP 任何东西，不改源库一个字节。
- 新实例侧唯一允许的写是 CREATE EXTENSION vector 与 restore 本身。
- 迁移完不会自动释放旧实例，也不会自动改 .env.ecs —— 切流仍需人工确认。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402

# 与 scripts/db_connect.py / apps.api.core.database 保持一致的会话守卫
SESSION_GUARD = (
    "-c idle_in_transaction_session_timeout=60s "
    "-c tcp_keepalives_idle=60 "
    "-c tcp_keepalives_interval=10 "
    "-c tcp_keepalives_count=5"
)

EXTENSIONS_REQUIRED = ("vector",)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def die(msg: str) -> NoReturn:
    log(f"❌ {msg}")
    sys.exit(1)


def parse_dsn(dsn: str) -> dict:
    """postgresql://user:pass@host:port/dbname -> psycopg2 kwargs"""
    p = urlparse(dsn)
    if p.scheme not in ("postgresql", "postgres"):
        die(f"DSN scheme 不是 postgresql: {p.scheme}")
    return {
        "host": p.hostname,
        "port": p.port or 5432,
        "user": unquote(p.username or ""),
        "password": unquote(p.password or ""),
        "dbname": (p.path or "/").lstrip("/"),
    }


def connect(dsn: str, **kw):
    params = parse_dsn(dsn)
    params.update(kw)
    return psycopg2.connect(options=SESSION_GUARD, connect_timeout=15, **params)


def q1(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------- 预检


def server_major(conn) -> int:
    """服务端大版本号（18 / 15.4 -> 18 / 15）"""
    raw = str(q1(conn, "SHOW server_version"))
    head = raw.split()[0]
    major = int(head.split(".")[0])
    # PG10 之前的 "9.6" 形式
    return major if major > 9 else int(head.split(".")[1])


def list_user_tables(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename FROM pg_tables
             WHERE schemaname = 'public'
               AND tablename NOT IN ('schema_migrations','spatial_ref_sys')
             ORDER BY tablename
            """
        )
        return [r[0] for r in cur.fetchall()]


def row_counts(conn) -> dict[str, int]:
    tables = list_user_tables(conn)
    out: dict[str, int] = {}
    with conn.cursor() as cur:
        for t in tables:
            # 表名来自 pg_tables，非外部输入；仍用格式安全的引号包裹
            cur.execute(f'SELECT COUNT(*) FROM public."{t}"')
            out[t] = cur.fetchone()[0]
    conn.rollback()
    return out


def ensure_database_exists(dst_dsn: str) -> None:
    """目标库必须已存在：RDS 新建实例上只有 postgres 一个库，不先处理会直接抛
    一个看不出所以然的 OperationalError traceback。先尝试用同一凭证建库，
    无权限时给出控制台的精确入口。"""
    try:
        connect(dst_dsn).close()
        return
    except psycopg2.OperationalError as e:
        if "does not exist" not in str(e):
            die(f"连不上目标库：{str(e)[:200]}")

    params = parse_dsn(dst_dsn)
    dbname = params["dbname"]
    log(f"  目标实例上还没有数据库 {dbname}，尝试创建…")
    admin = dict(params, dbname="postgres")
    try:
        conn = psycopg2.connect(options=SESSION_GUARD, connect_timeout=15, **admin)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                f'CREATE DATABASE "{dbname}" ENCODING \'UTF8\' TEMPLATE template0'
            )
        conn.close()
        log(f"  ✅ 已创建数据库 {dbname}")
    except Exception as e:  # noqa: BLE001
        die(
            f"自动建库失败：{str(e)[:160]}\n"
            f"   请在控制台手工建库：RDS 实例 {params['host'].split('.')[0]} → 左侧「数据库管理」→\n"
            f"   创建数据库，库名填 {dbname}，字符集选 UTF8，授权账号选你的连接账号。"
        )


def preflight(src_dsn: str, dst_dsn: str, pg_bin: str, force: bool) -> dict:
    log("── 阶段 0：预检 ──")
    info: dict = {}

    src = connect(src_dsn)
    ensure_database_exists(dst_dsn)
    dst = connect(dst_dsn)

    src_major, dst_major = server_major(src), server_major(dst)
    info["src_major"], info["dst_major"] = src_major, dst_major
    log(f"  源端 PostgreSQL {src_major} / 目标端 PostgreSQL {dst_major}")

    if dst_major < src_major:
        src.close(); dst.close()
        die(
            f"目标端大版本（{dst_major}）低于源端（{src_major}）。pg_restore 不支持向"
            f"低版本恢复，回退路径会被堵死。请在创建页把新实例引擎版本选到 ≥{src_major}。"
        )

    # pgvector 必须在新实例可用 —— 这是整个方案能否成立的前提
    with dst.cursor() as cur:
        for ext in EXTENSIONS_REQUIRED:
            cur.execute(
                "SELECT default_version FROM pg_available_extensions WHERE name = %s", (ext,)
            )
            row = cur.fetchone()
            if not row:
                src.close(); dst.close()
                die(
                    f"目标端引擎没有 {ext} 扩展，items.embedding 无处安放。"
                    f"请换 RDS PostgreSQL 版本（控制台 → 可维护参数/扩展列表确认），不要继续。"
                )
            log(f"  目标端 {ext} 可用，版本 {row[0]}")

    # 目标端必须为空库
    dst_tables = list_user_tables(dst)
    if dst_tables and not force:
        src.close(); dst.close()
        die(
            f"目标库已有 {len(dst_tables)} 张表（{', '.join(dst_tables[:5])} ...）。"
            f"确认是空库以外的场景请加 --force。"
        )
    log(f"  目标库现有业务表 {len(dst_tables)} 张")

    # pg_dump / pg_restore 客户端版本必须 ≥ 源端服务端版本
    dump_ver = pg_client_version(pg_bin, "pg_dump")
    if dump_ver is None:
        src.close(); dst.close()
        die(
            f"找不到可用的 pg_dump（pg-bin={pg_bin!r}）。ECS 上可装 postgresql-client，"
            f"或用 --pg-bin 'docker run --rm -i postgres:{src_major}' 借容器里的新版客户端。"
        )
    info["pg_dump_major"] = dump_ver
    log(f"  pg_dump 客户端版本 {dump_ver}")
    if dump_ver < src_major:
        src.close(); dst.close()
        die(
            f"pg_dump 客户端（{dump_ver}）低于源端服务端（{src_major}），"
            f"pg_dump 会直接拒绝执行。请用 --pg-bin 指定 ≥{src_major} 的客户端。"
        )
    restore_ver = pg_client_version(pg_bin, "pg_restore")
    if restore_ver is None or restore_ver < src_major:
        src.close(); dst.close()
        die(f"pg_restore 同样需要 ≥{src_major} 版本（当前 {restore_ver}）。")
    log(f"  pg_restore 客户端版本 {restore_ver}")

    # 归档走 stdin/stdout 管道，docker exec/run 不加 -i 时 stdin 不会接入容器；
    # 带 -t 则会给输出加 CR 换行、损坏 binary 归档，两者都要在预检拦住。
    if "docker" in pg_bin:
        tokens = pg_bin.split()
        if "-i" not in tokens:
            src.close(); dst.close()
            fixed = pg_bin.replace("docker exec", "docker exec -i", 1).replace("docker run", "docker run -i", 1)
            die(f"--pg-bin 用了 docker 但没带 -i，pg_restore 无法从 stdin 读入归档。\n"
                f"   请改为：--pg-bin \"{fixed}\"")
        if any(t.startswith("-") and t.endswith("t") and "i" in t for t in tokens):
            src.close(); dst.close()
            die("--pg-bin 里的 docker 带了 -t：tty 会把 binary 归档译成带 CR 的文本，"
                "数据会静默损坏。请只用 -i，不要 -t。")
    log(f"  pg 客户端来源：{pg_bin or '本机 PATH'}")

    # 源端健康度顺带报一下：idle in transaction 会让 dump 拖长并加剧膨胀
    idle_tx = q1(
        src,
        "SELECT COUNT(*) FROM pg_stat_activity "
        "WHERE state = 'idle in transaction' AND pid <> pg_backend_pid()",
    )
    if idle_tx:
        log(f"  ⚠ 源端仍有 {idle_tx} 个 idle in transaction 会话（建议先清理再迁，"
            f"否则 dump 的快照点会被这些老事务影响）")
    else:
        log("  源端无 idle in transaction 残留 ✓")

    info["src_tables"] = list_user_tables(src)
    info["src_rows"] = row_counts(src)
    log(f"  源端业务表 {len(info['src_tables'])} 张，合计 {sum(info['src_rows'].values())} 行")

    src.close(); dst.close()
    return info


def resolve(pg_bin: str, tool: str) -> list[str]:
    """把 pg_bin 前缀展开成命令数组

    docker 形式会自动补 -e PGPASSWORD：docker exec/run 不会把宿主机环境变量带进容器，
    不转发的话 pg_dump 连 RDS 时会要求交互输入密码（stdin 已接管道，会直接失败）。
    用不带值的 -e VAR 形式，避免密码出现在 ps 输出里。
    """
    prefix = pg_bin.split() if pg_bin else []
    if len(prefix) >= 2 and prefix[0] == "docker" and prefix[1] in ("exec", "run"):
        prefix[2:2] = ["-e", "PGPASSWORD"]
    return prefix + [tool]


def pg_client_version(pg_bin: str, tool: str) -> int | None:
    cmd = resolve(pg_bin, tool) + ["--version"]
    # 给个空的 PGPASSWORD 占位，否则 docker 会对 -e PGPASSWORD 报"未设置"警告（走 stderr）
    env = {**os.environ, "PGPASSWORD": os.environ.get("PGPASSWORD", "")}
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, env=env
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    # 形如 "pg_dump (PostgreSQL) 18.0"
    tok = out.stdout.strip().split()[-1]
    try:
        head = tok.split(".")[0]
        return int(head) if int(head) > 9 else int(tok.split(".")[1])
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------- 搬迁


def dump(src_dsn: str, pg_bin: str, dump_path: Path) -> None:
    log("── 阶段 1：导出源库 ──")
    params = parse_dsn(src_dsn)
    env = {**os.environ, "PGPASSWORD": params["password"]}
    # 归档走 stdout/stdin 管道而不是 -f 文件路径：pg_bin 是 docker exec 时，容器内根本
    # 没有宿主机上的 backups/ 目录，直传路径会报 "No such file or directory"。
    # 注意不能写 "-f -"：pg_dump 会把它当成一个字面叫 "-" 的文件（rc=0、无报错、
    # stdout 零字节的完美假成功），省掉 -f 才是默认输出到标准输出。
    cmd = resolve(pg_bin, "pg_dump") + [
        "-h", str(params["host"]), "-p", str(params["port"]),
        "-U", params["user"], "-d", params["dbname"],
        "-Fc", "--no-owner", "--no-privileges",
    ]
    log(f"  执行 pg_dump（数据量小，通常几秒）")
    with open(dump_path, "wb") as fh:
        res = subprocess.run(
            cmd, env=env, timeout=1800, stderr=subprocess.PIPE, stdout=fh, stdin=subprocess.DEVNULL,
            text=True,
        )
    if res.returncode != 0:
        dump_path.unlink(missing_ok=True)
        die(f"pg_dump 失败: {res.stderr[:600]}")
    size_bytes = dump_path.stat().st_size
    if size_bytes < 1024:
        die(f"pg_dump 返回成功但归档只有 {size_bytes} 字节，疑似输出被截断或被 tty 破坏，中止")
    log(f"  ✅ 导出完成：{dump_path} ({size_bytes / 1024 / 1024:.2f} MB)")


def restore(dst_dsn: str, pg_bin: str, dump_path: Path) -> None:
    log("── 阶段 2：导入目标库 ──")
    params = parse_dsn(dst_dsn)
    env = {**os.environ, "PGPASSWORD": params["password"]}

    # vector 扩展必须在 restore 之前存在，否则含 vector 列的 CREATE TABLE 会失败；
    # 先建还能顺带避开一个坑：dump 里带的是源端旧版本号（如 VERSION '0.5.1'），
    # 若该版本在新实例上不可用会报错，而已存在时 IF NOT EXISTS 会直接跳过不校验版本。
    log("  预建扩展：vector")
    dst = connect(dst_dsn)
    dst.autocommit = True
    with dst.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    dst.close()

    # 归档从 stdin 送入（pg_restore 不给位置参数时默认读标准输入），同样是为了
    # 避开宿主机/容器路径不一致；docker 形式需带 -i
    cmd = resolve(pg_bin, "pg_restore") + [
        "-h", str(params["host"]), "-p", str(params["port"]),
        "-U", params["user"], "-d", params["dbname"],
        "--no-owner", "--no-privileges", "--no-comments",
    ]
    log(f"  pg_restore → {params['host']}:{params['port']}/{params['dbname']}")
    with open(dump_path, "rb") as fh:
        res = subprocess.run(
            cmd, env=env, timeout=1800, stderr=subprocess.PIPE, text=True, stdin=fh
        )
    # pg_restore 对可恢复问题返回 1，需按 stderr 里的 ERROR 数量判定真实成败
    err_lines = [l for l in (res.stderr or "").splitlines() if l.startswith("pg_restore: error:")]
    if res.returncode != 0 and err_lines:
        log(f"  ⚠ pg_restore 报告 {len(err_lines)} 条 error：")
        for l in err_lines[:12]:
            print(f"      {l[:200]}")
        if not force_ok(err_lines):
            die("存在实质性失败，请上面的 error 逐条确认后再决定是否重跑（--force 覆盖空库检查）。")
    log("  ✅ 导入完成")


BENIGN_HINTS = ("already exists", "must be owner", "extension \"vector\"")


def force_ok(err_lines: list[str]) -> bool:
    """全部错误都是无害噪音（扩展重复创建/属主权限）时放行"""
    return all(any(h in l.lower() for h in BENIGN_HINTS) for l in err_lines)


# ---------------------------------------------------------------- 校验


def verify(src_dsn: str, dst_dsn: str) -> bool:
    log("── 阶段 3：一致性校验 ──")
    src, dst = connect(src_dsn), connect(dst_dsn)
    src_rows, dst_rows = row_counts(src), row_counts(dst)

    ok = True
    missing = set(src_rows) - set(dst_rows)
    extra = set(dst_rows) - set(src_rows)
    if missing:
        log(f"  ❌ 目标端缺表 {len(missing)}：{', '.join(sorted(missing)[:8])}")
        ok = False
    if extra:
        log(f"  ⚠ 目标端多出表 {len(extra)}：{', '.join(sorted(extra)[:8])}")

    diff = {t: (src_rows[t], dst_rows[t]) for t in src_rows
            if t in dst_rows and src_rows[t] != dst_rows[t]}
    if diff:
        log(f"  ❌ {len(diff)} 张表行数不一致：")
        for t, (s, d) in sorted(diff.items())[:15]:
            print(f"      {t:<32} 源 {s:>8}  目标 {d:>8}")
        ok = False
    else:
        log(f"  ✅ {len(src_rows)} 张表行数逐张一致，合计 {sum(src_rows.values())} 行")

    # 向量检索能力：embedding 非空数与 HNSW 索引
    for probe, sql in (
        (
            "items embedding 非空数",
            "SELECT COUNT(*) FROM items WHERE embedding IS NOT NULL",
        ),
        (
            "向量索引存在数",
            "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public' AND indexdef ILIKE '%vector%'",
        ),
    ):
        try:
            s, d = q1(src, sql), q1(dst, sql)
        except Exception as e:  # noqa: BLE001
            src.rollback(); dst.rollback()
            log(f"  ⚠ {probe} 探测失败（不影响主结论）: {e}")
            continue
        flag = "✅" if s == d else "❌"
        log(f"  {flag} {probe}: 源 {s} / 目标 {d}")
        if s != d:
            ok = False

    src_size = q1(src, "SELECT pg_database_size(current_database())")
    dst_size = q1(dst, "SELECT pg_database_size(current_database())")
    log(f"  库体积：源 {src_size/1024/1024:.1f} MB / 目标 {dst_size/1024/1024:.1f} MB")

    src.close(); dst.close()
    return ok


# ---------------------------------------------------------------- 主流程


def load_src_default() -> str | None:
    """源库默认值：已导出的 DATABASE_URL 优先，其次读 .env.ecs（ECS 上脚本跑在容器外）"""
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    env_file = ROOT / ".env.ecs"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL=") and not line.startswith("#"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="把生产库搬迁到新的 RDS PostgreSQL 实例")
    ap.add_argument("--src", default=load_src_default(), help="源库 DSN，默认取 .env.ecs 的 DATABASE_URL")
    ap.add_argument("--dst", default=os.getenv("DST_DATABASE_URL"),
                    help="新实例 DSN；推荐用环境变量 DST_DATABASE_URL 传入，避免密码出现在 ps/历史记录")
    ap.add_argument("--pg-bin", default="", help="pg_dump/pg_restore 命令前缀，如 'docker run --rm -i postgres:18'")
    ap.add_argument("--dump-file", default="", help="中间 dump 路径，默认 backups/migrate_<ts>.dump")
    ap.add_argument("--keep-dump", action="store_true", help="保留 dump 文件（默认校验通过后删除）")
    ap.add_argument("--force", action="store_true", help="目标库非空时仍继续")
    ap.add_argument("--yes", action="store_true", help="跳过写入确认（非交互环境必须带）")
    ap.add_argument("--verify-only", action="store_true", help="只跑校验，不搬迁")
    args = ap.parse_args()

    if not args.dst:
        die("未提供目标库：请用 --dst 或环境变量 DST_DATABASE_URL 传入")
    if not args.src:
        die("找不到源库 DSN，请显式传 --src")
    def ep(dsn: str) -> tuple:
        d = parse_dsn(dsn)
        return (d["host"], d["port"], d["dbname"])

    if ep(args.src) == ep(args.dst):
        die(f"源库与目标库是同一个库（{ep(args.src)}），这不叫迁移")

    ts = time.strftime("%Y%m%d_%H%M%S")
    dump_path = Path(args.dump_file) if args.dump_file else ROOT / "backups" / f"migrate_{ts}.dump"
    dump_path.parent.mkdir(parents=True, exist_ok=True)

    if args.verify_only:
        return 0 if verify(args.src, args.dst) else 1

    info = preflight(args.src, args.dst, args.pg_bin, args.force)

    if info["src_rows"] and sum(info["src_rows"].values()) > 0 and not args.yes:
        log("⚠ 迁移期间请确保没有新数据写入源库（否则 dump 快照与切流后的新库会不一致）：")
        log("   docker compose -f docker-compose.prod.yml stop api worker   # 约 1 分钟")
        if not sys.stdin.isatty():
            die("非交互环境无法确认，请先停掉写入再带 --yes 重跑。")
        if input("   已停写入？继续请输入 yes：").strip().lower() != "yes":
            die("已取消。停掉写入后重跑即可。")

    dump(args.src, args.pg_bin, dump_path)
    restore(args.dst, args.pg_bin, dump_path)

    if not verify(args.src, args.dst):
        log("❌ 校验未通过。旧实例保持原样，切流前先按上面差异修复。")
        log(f"   dump 文件留档在 {dump_path}")
        return 1

    if not args.keep_dump:
        dump_path.unlink(missing_ok=True)
        log("  dump 文件已删除（加 --keep-dump 可保留）")
    else:
        log(f"  dump 文件保留在 {dump_path}")

    print()
    log("✅ 迁移完成且校验通过。接下来的动作（都需人工确认，本脚本不代做）：")
    print("   1) 改 ECS 上的 .env.ecs（该文件不在 git 里，必须手工改）：")
    print(f"        DATABASE_URL=<本次 --dst 的值>")
    print("   2) 重启并观察：")
    print("        docker compose -f docker-compose.prod.yml up -d api worker")
    print("        docker compose -f docker-compose.prod.yml logs -f api | grep -i -E 'error|迁移|连接池'")
    print("      首次启动日志应出现「发现 1 个待执行迁移 / 迁移成功: 29_bill_item_drilldown.sql」")
    print("   3) 页面点一轮主链路：推荐、衣橱、日记、运势、海报、后台账单看板")
    print("   4) 稳定后再在控制台释放旧实例（最多留 3 天，每天约 10.5 元）")
    print("   5) 观察 2 周无异常 → 控制台把新实例「变更计费方式」为包年包月")
    return 0


if __name__ == "__main__":
    sys.exit(main())
