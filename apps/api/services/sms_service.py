"""
短信验证码服务（阿里云号码认证服务 - 短信认证）

个人备案场景选用阿里云「短信认证」(PNVS)：
- 无需企业资质、免签名/模板审核（使用系统赠送签名与标准验证码模板）
- 验证码由平台生成与核验（SendSmsVerifyCode + CheckSmsVerifyCode 闭环），本项目不落库明文验证码
- 凭证优先级：config 显式 AK/SK > 默认凭证链（ECS 实例 RAM 角色 / 环境变量）

sms_enabled=False（开发/测试环境）时：发送仅打印日志，核验使用固定码 DEV_VERIFY_CODE，不消耗付费额度。
安全约束（fail-closed）：生产环境（app_env=production）下若 sms_enabled=False，
发送直接抛错、核验直接拒绝，固定码降级分支不可达，杜绝绕过实名验证注册。
"""

import logging
import threading

from apps.api.core.config import settings

logger = logging.getLogger(__name__)

# 开发模式固定验证码（仅 sms_enabled=False 时生效）
DEV_VERIFY_CODE = "123456"

# 号码认证服务端点
SMS_ENDPOINT = "dypnsapi.aliyuncs.com"


class SmsServiceError(Exception):
    """短信服务异常（配置缺失/调用失败）"""


class SmsService:
    """短信认证客户端（懒加载单例，复用底层 HTTP 连接）"""

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        """懒初始化并复用 DypnsApi 客户端"""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from alibabacloud_dypnsapi20170525.client import Client as DypnsClient
                    from alibabacloud_tea_openapi import models as open_api_models

                    config = open_api_models.Config()
                    if settings.aliyun_sms_access_key_id and settings.aliyun_sms_access_key_secret:
                        # 方式 B：显式 AK/SK（本地开发，RAM 用户）
                        config.access_key_id = settings.aliyun_sms_access_key_id
                        config.access_key_secret = settings.aliyun_sms_access_key_secret
                    else:
                        # 方式 A：默认凭证链（生产 ECS 实例 RAM 角色免 AK）
                        from alibabacloud_credentials.client import Client as CredentialClient
                        config.credential = CredentialClient()
                    config.endpoint = SMS_ENDPOINT
                    self._client = DypnsClient(config)
        return self._client

    async def send_verify_code(self, phone: str) -> None:
        """
        发送短信验证码（验证码由平台生成并管理有效期，发送失败不计费）

        Raises:
            SmsServiceError: 云端调用失败
        """
        if not settings.sms_enabled:
            if settings.is_production:
                # fail-closed：生产环境绝不允许走固定码降级分支
                raise SmsServiceError("短信服务未启用，请稍后重试")
            logger.info(
                "[短信][DEV] 开发模式不真实发送，固定验证码 %s: %s****%s",
                DEV_VERIFY_CODE, phone[:3], phone[7:],
            )
            return

        from alibabacloud_dypnsapi20170525 import models as dypns_models
        from alibabacloud_tea_util import models as util_models

        request = dypns_models.SendSmsVerifyCodeRequest(
            phone_number=phone,
            sign_name=settings.aliyun_sms_sign_name,
            template_code=settings.aliyun_sms_template_code,
            # 赠送模板含两个变量：验证码 + 有效期(分钟)
            # "##code##" 占位符由平台生成验证码，CheckSmsVerifyCode 才能闭环核验
            template_param='{"code":"##code##","min":"5"}',
            code_type=1,      # 纯数字
            code_length=6,    # 6 位验证码（与前端 maxLength=6 对齐）
            duplicate_policy=2,  # 重发保留旧码（有效期内均可用），避免用户填上一条短信的码被拒
        )
        try:
            resp = await self._get_client().send_sms_verify_code_with_options_async(
                request, util_models.RuntimeOptions()
            )
        except Exception as e:
            logger.error("[短信] 验证码发送调用失败: %s", e)
            raise SmsServiceError("验证码发送失败，请稍后重试") from e

        if getattr(resp.body, "code", "") != "OK":
            logger.error(
                "[短信] 验证码发送被拒: %s %s",
                getattr(resp.body, "code", ""), getattr(resp.body, "message", ""),
            )
            raise SmsServiceError("验证码发送失败，请稍后重试")
        logger.info("[短信] 验证码已发送: %s****%s", phone[:3], phone[7:])

    async def verify_code(self, phone: str, code: str) -> bool:
        """
        核验短信验证码（平台闭环校验，含有效期与防暴力破解）

        Returns:
            True 核验通过
        Raises:
            SmsServiceError: 云端调用失败
        """
        if not settings.sms_enabled:
            if settings.is_production:
                # fail-closed：生产环境固定码不可用
                return False
            return code == DEV_VERIFY_CODE

        from alibabacloud_dypnsapi20170525 import models as dypns_models
        from alibabacloud_tea_util import models as util_models

        request = dypns_models.CheckSmsVerifyCodeRequest(
            phone_number=phone,
            verify_code=code,
        )
        try:
            resp = await self._get_client().check_sms_verify_code_with_options_async(
                request, util_models.RuntimeOptions()
            )
        except Exception as e:
            # isv.ValidateFail = 码错误/已失效，属业务结果而非服务故障
            if "ValidateFail" in str(e):
                logger.info("[短信] 验证码核验未通过: %s****%s", phone[:3], phone[7:])
                return False
            logger.error("[短信] 验证码核验调用失败: %s", e)
            raise SmsServiceError("验证码核验失败，请稍后重试") from e

        # VerifyResult 嵌套在 body.model 下：PASS=核验成功 / UNKNOWN=核验失败
        # 注意：验证码为一次性消耗品，核验成功即失效
        if getattr(resp.body, "code", "") != "OK":
            return False
        model = getattr(resp.body, "model", None)
        return getattr(model, "verify_result", "") == "PASS"


# 全局单例
sms_service = SmsService()
