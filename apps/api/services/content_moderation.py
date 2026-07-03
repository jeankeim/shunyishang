"""
内容审核服务 - 敏感词过滤
轻量级关键词匹配，不依赖外部审核 API
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# 敏感词列表（基础版，可按需扩展）
_SENSITIVE_WORDS = [
    # 政治敏感
    "法轮功", "法輪功", "翻墙", "vpn",
    # 广告/引流
    "加微信", "加我微信", "微信号", "扫码加", "免费领取",
    "点击链接", "复制口令", "拼多多", "砍一刀",
    # 违规内容
    "赌博", "博彩", "色情", "约炮", "裸聊",
    # 辱骂
    "傻逼", "妈逼", "操你", "去死", "滚蛋",
]

# 编译正则（忽略大小写）
_PATTERN = re.compile(
    "|".join(re.escape(w) for w in _SENSITIVE_WORDS),
    re.IGNORECASE,
)


def check_content(text: str) -> Tuple[bool, str]:
    """
    检查文本内容是否合规

    Returns:
        (is_pass, reason)
        is_pass=True 表示内容合规
        is_pass=False 时 reason 说明原因
    """
    if not text or not text.strip():
        return False, "内容不能为空"

    if len(text) > 2000:
        return False, "内容过长"

    match = _PATTERN.search(text)
    if match:
        logger.info(f"[内容审核] 检测到敏感词: {match.group()}")
        return False, "内容包含不当词汇，请修改后重新发布"

    return True, ""


def check_images(image_urls: list) -> Tuple[bool, str]:
    """基础图片 URL 校验（确保非空 URL 列表合法）"""
    if len(image_urls) > 9:
        return False, "最多上传 9 张图片"

    for url in image_urls:
        if not url or not url.startswith(("http://", "https://")):
            return False, "图片链接格式不正确"

    return True, ""
