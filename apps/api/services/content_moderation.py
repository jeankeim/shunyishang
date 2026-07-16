"""
内容审核服务 - 敏感词过滤
轻量级关键词匹配 + 文本归一化变体检测，支持外部词库热加载
预留外部审核 API 接口（阿里云内容安全等）
"""

import re
import os
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 敏感词库加载（启动时一次性读取，避免每次调用都读文件）
# ─────────────────────────────────────────────
_SENSITIVE_WORDS_PATH = Path(__file__).resolve().parents[3] / "data" / "standards" / "sensitive_words.txt"


def _load_sensitive_words(path: Path) -> list:
    """从外部文件加载敏感词库，忽略注释行和空行"""
    words = []
    if not path.exists():
        logger.warning(f"[内容审核] 敏感词库文件不存在: {path}，使用内置兜底词库")
        return _FALLBACK_WORDS
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    words.append(line)
    except Exception as e:
        logger.error(f"[内容审核] 加载敏感词库失败: {e}，使用内置兜底词库")
        return _FALLBACK_WORDS
    logger.info(f"[内容审核] 已加载 {len(words)} 个敏感词（来源: {path.name}）")
    return words


# 兜底词库（文件加载失败时使用，保持向后兼容）
_FALLBACK_WORDS = [
    "法轮功", "法輪功", "翻墙", "vpn",
    "加微信", "加我微信", "微信号", "扫码加", "免费领取",
    "点击链接", "复制口令", "拼多多", "砍一刀",
    "赌博", "博彩", "色情", "约炮", "裸聊",
    "傻逼", "妈逼", "操你", "去死", "滚蛋",
]

# 启动时加载
_SENSITIVE_WORDS: list = _load_sensitive_words(_SENSITIVE_WORDS_PATH)

# 编译正则（忽略大小写）
_PATTERN = re.compile(
    "|".join(re.escape(w) for w in _SENSITIVE_WORDS),
    re.IGNORECASE,
)


# ─────────────────────────────────────────────
# 文本归一化：处理谐音字、拆字、特殊字符干扰
# ─────────────────────────────────────────────

# 谐音 / 形近字映射表（归一化到标准写法）
_HOMOPHONE_MAP = {
    # 微信变体
    "威": "微",
    "围": "微",
    "薇": "微",
    "惟": "微",
    "维": "微",
    "卫": "微",
    # Q/QQ 变体
    "扣": "Q",
    "叩": "Q",
    "寇": "Q",
    # 其他常见谐音
    "威信": "微信",
    "卫星": "微信",
    "薇信": "微信",
    "围信": "微信",
}

# 用于移除字间干扰字符（如 微.信 → 微信，加*我 → 加我）
_NOISE_CHAR_PATTERN = re.compile(
    r"(?<=[\u4e00-\u9fff])[.\-*~·•|/\\@#$%^&+=!！,，;；:：\s]{1,3}(?=[\u4e00-\u9fffA-Za-z])"
)

# V/v 在"信"前也视为"微"（需单独处理，因为是英文字母）
_VX_PATTERN = re.compile(r"[Vv][\s.\-*~]*信", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    """
    文本归一化：处理谐音字、拆字、特殊字符干扰

    处理顺序：
    1. 移除中文字符间的噪声符号（微.信 → 微信）
    2. V/v + 信 → 微信
    3. 逐词谐音替换
    """
    # 1. 移除字间干扰字符
    text = _NOISE_CHAR_PATTERN.sub("", text)

    # 2. V/v 信 → 微信
    text = _VX_PATTERN.sub("微信", text)

    # 3. 多字谐音词替换（先处理长词，再处理单字）
    for variant, standard in sorted(_HOMOPHONE_MAP.items(), key=lambda x: -len(x[0])):
        text = text.replace(variant, standard)

    return text


# ─────────────────────────────────────────────
# 文本长度分级限制
# ─────────────────────────────────────────────
CONTENT_LENGTH_LIMITS = {
    "title":   100,    # 帖子标题
    "post":    5000,   # 帖子正文
    "comment": 1000,   # 评论
    "default": 2000,   # 通用默认值（向后兼容）
}


# ─────────────────────────────────────────────
# 核心审核函数（保持原有签名，向后兼容）
# ─────────────────────────────────────────────

def check_content(text: str, content_type: str = "default") -> Tuple[bool, str]:
    """
    检查文本内容是否合规

    Args:
        text: 待审核文本
        content_type: 内容类型，可选 "title" / "post" / "comment" / "default"

    Returns:
        (is_pass, reason)
        is_pass=True 表示内容合规
        is_pass=False 时 reason 说明原因
    """
    if not text or not text.strip():
        return False, "内容不能为空"

    max_len = CONTENT_LENGTH_LIMITS.get(content_type, CONTENT_LENGTH_LIMITS["default"])
    if len(text) > max_len:
        return False, f"内容过长，最多 {max_len} 字"

    # 先对原文匹配
    match = _PATTERN.search(text)
    if match:
        logger.info(f"[内容审核] 检测到敏感词: {match.group()}")
        return False, "内容包含不当词汇，请修改后重新发布"

    # 归一化后再匹配（捕捉变体绕过）
    normalized = _normalize_text(text)
    if normalized != text:
        match = _PATTERN.search(normalized)
        if match:
            logger.info(f"[内容审核] 归一化后检测到敏感词: {match.group()}（原文变体）")
            return False, "内容包含不当词汇，请修改后重新发布"

    return True, ""


def moderate_text(text: str, content_type: str = "default") -> Tuple[bool, str]:
    """
    check_content 的别名，提供更语义化的调用入口
    签名与 check_content 完全一致，方便外部使用
    """
    return check_content(text, content_type=content_type)


def check_images(image_urls: list) -> Tuple[bool, str]:
    """基础图片 URL 校验（确保非空 URL 列表合法）"""
    if len(image_urls) > 9:
        return False, "最多上传 9 张图片"

    for url in image_urls:
        if not url or not url.startswith(("http://", "https://")):
            return False, "图片链接格式不正确"

    return True, ""


# ─────────────────────────────────────────────
# 预留：外部审核 API 接口（阿里云内容安全等）
# ─────────────────────────────────────────────

async def check_content_with_api(text: str, image_url: Optional[str] = None) -> dict:
    """
    预留：接入阿里云内容安全 API

    当需要接入第三方审核时，替换本函数实现即可。
    当前直接放行，不影响业务逻辑。

    Args:
        text: 待审核文本
        image_url: 待审核图片 URL（可选）

    Returns:
        {"passed": bool, "reason": Optional[str]}
    """
    # TODO: 接入阿里云内容安全
    return {"passed": True, "reason": None}
