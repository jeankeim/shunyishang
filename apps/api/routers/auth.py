"""
用户认证路由模块
提供注册、登录、用户信息管理
"""

import json
import logging
import os
import re
from datetime import timedelta, datetime, date, time
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr

from apps.api.core.database import DatabasePool

logger = logging.getLogger(__name__)
from apps.api.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    generate_user_code
)
from apps.api.core.config import settings
from apps.api.core.rate_limit import auth_rate_limit, check_rate_limit
from apps.api.core.pii_crypto import encrypt_pii, decrypt_pii, decrypt_date, decrypt_time
from apps.api.services.sms_service import sms_service, SmsServiceError
from packages.utils.bazi_calculator import calculate_bazi

router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 大陆手机号格式（防虚构/无效号码浪费短信额度）
PHONE_REGEX = r"^1[3-9]\d{9}$"


# ========== 请求/响应模型 ==========

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    phone: Optional[str] = Field(None, description="手机号")
    sms_code: Optional[str] = Field(None, description="短信验证码（开启短信验证后必填）")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    nickname: Optional[str] = Field(None, description="昵称")
    gender: Optional[str] = Field(None, pattern="^(男|女)?$", description="性别")
    privacy_consent: bool = Field(False, description="是否已同意隐私政策（PIPL 必须为 true）")


class SmsSendRequest(BaseModel):
    """短信验证码发送请求"""
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="大陆手机号")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    user_code: str
    phone: Optional[str]
    email: Optional[str]
    nickname: Optional[str]
    gender: Optional[str]
    birth_date: Optional[date]
    birth_time: Optional[time]
    birth_location: Optional[str]
    preferred_city: Optional[str]
    avatar_url: Optional[str]
    bazi: Optional[dict]
    xiyong_elements: Optional[list]


class TokenResponse(BaseModel):
    """登录令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UpdateBaziRequest(BaseModel):
    """更新八字请求"""
    birth_year: int = Field(..., ge=1900, le=2100)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_hour: int = Field(..., ge=0, le=23)
    gender: str = Field(..., pattern="^(男|女)$")
    sensitive_consent: bool = Field(False, description="是否单独同意处理出生信息（PIPL 敏感信息，必须为 true）")


class UpdateProfileRequest(BaseModel):
    """更新用户资料请求"""
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    gender: Optional[str] = Field(None, pattern="^(男|女)?$", description="性别")
    birth_date: Optional[date] = Field(None, description="出生日期")
    birth_time: Optional[time] = Field(None, description="出生时间")
    birth_location: Optional[str] = Field(None, max_length=200, description="出生地点")
    preferred_city: Optional[str] = Field(None, max_length=100, description="常驻城市")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    # Week 4: 审美画像字段
    skin_tone: Optional[str] = Field(None, max_length=20, description="肤色: 冷白皮/暖白皮/自然色/小麦色/黑皮")
    style_preference: Optional[str] = Field(None, max_length=50, description="风格偏好: 简约/韩系/日系/国潮/复古/商务/街头/文艺")
    body_type: Optional[str] = Field(None, max_length=20, description="体型: 偏瘦/标准/偏胖")
    aesthetic_tags: Optional[List[str]] = Field(None, description="扩展审美标签数组")
    sensitive_consent: bool = Field(False, description="更新出生信息时需单独同意（PIPL 敏感信息）")


class UserProfileResponse(BaseModel):
    """完整用户资料响应"""
    id: int
    user_code: str
    phone: Optional[str]
    email: Optional[str]
    nickname: Optional[str]
    gender: Optional[str]
    birth_date: Optional[date]
    birth_time: Optional[time]
    birth_location: Optional[str]
    preferred_city: Optional[str]
    avatar_url: Optional[str]
    bazi: Optional[dict]
    xiyong_elements: Optional[list]
    # Week 4: 审美画像字段
    skin_tone: Optional[str] = None
    style_preference: Optional[str] = None
    body_type: Optional[str] = None
    aesthetic_tags: Optional[list] = None
    created_at: datetime
    updated_at: datetime


# ========== 依赖函数 ==========

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # 查询用户
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_code, phone, email, nickname, gender, 
                       birth_date, birth_time, birth_location, preferred_city,
                       avatar_url, bazi, xiyong_elements, is_active
                FROM users WHERE id = %s
                """,
                (user_id,)
            )
            row = cur.fetchone()
            
            if row is None or not row[13]:  # is_active
                raise credentials_exception
            
            return {
                "id": row[0],
                "user_code": row[1],
                "phone": row[2],
                "email": row[3],
                "nickname": row[4],
                "gender": row[5],
                "birth_date": decrypt_date(row[6]),
                "birth_time": decrypt_time(row[7]),
                "birth_location": decrypt_pii(row[8]),
                "preferred_city": row[9],
                "avatar_url": row[10],
                "bazi": row[11],
                "xiyong_elements": row[12],
            }


# ========== 路由 ==========

@router.post("/sms/send", summary="发送短信验证码",
             dependencies=[Depends(auth_rate_limit)])
async def send_sms_code(request: SmsSendRequest):
    """
    发送注册短信验证码

    **核心逻辑**:
    1. IP 级限流（auth_rate_limit 依赖）
    2. 同号每日 ≤5 次 + 60 秒重发间隔（防短信轰炸）
    3. 调用阿里云短信认证发送（验证码由平台生成与托管）
    """
    # 每日上限：同一号码每天最多 5 次
    allowed, _ = await check_rate_limit(f"sms:day:{request.phone}", 5, 86400)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今日发送次数已达上限，请明天再试"
        )

    # 重发间隔：同一号码 60 秒内最多 1 次
    allowed, retry_after = await check_rate_limit(f"sms:cd:{request.phone}", 1, 60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"验证码已发送，请 {retry_after} 秒后重试",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        await sms_service.send_verify_code(request.phone)
    except SmsServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {"message": "验证码已发送", "expires_in": 300}


@router.post("/register", response_model=TokenResponse, summary="用户注册",
             dependencies=[Depends(auth_rate_limit)])
async def register(request: UserRegisterRequest):
    """
    用户注册
    
    **核心逻辑**:
    1. PIPL：注册必须先同意隐私政策
    2. 手机号格式校验 + 短信验证码核验（sms_enabled 时强制）
    3. fail-closed：生产环境未开启短信开关时拒绝注册
    4. 检查手机号/邮箱是否已注册
    5. 生成 user_code 和密码哈希
    6. 插入用户数据到数据库
    7. 生成 JWT token 返回
    """
    # PIPL：注册必须先同意隐私政策
    if not request.privacy_consent:
        raise HTTPException(
            status_code=400,
            detail="请先阅读并同意隐私政策"
        )

    # 手机号格式校验：拒绝虚构/无效号码
    if request.phone and not re.match(PHONE_REGEX, request.phone):
        raise HTTPException(
            status_code=400,
            detail="手机号格式不正确"
        )

    # fail-closed：生产环境必须开启短信验证，防止配置疏漏导致绕过实名注册
    if settings.is_production and not settings.sms_enabled:
        raise HTTPException(
            status_code=503,
            detail="注册服务配置异常，请稍后重试"
        )

    # 短信实名验证：开启后注册必须提供手机号并通过验证码核验
    if settings.sms_enabled:
        if not request.phone:
            raise HTTPException(
                status_code=400,
                detail="注册必须提供手机号"
            )
        if not request.sms_code:
            raise HTTPException(
                status_code=400,
                detail="请输入短信验证码"
            )
        try:
            verified = await sms_service.verify_code(request.phone, request.sms_code)
        except SmsServiceError as e:
            raise HTTPException(status_code=503, detail=str(e))
        if not verified:
            raise HTTPException(
                status_code=400,
                detail="验证码错误或已失效"
            )
    elif not request.phone and not request.email:
        raise HTTPException(
            status_code=400,
            detail="手机号或邮箱至少提供一个"
        )
    
    # 检查是否已存在
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            if request.phone:
                cur.execute("SELECT id FROM users WHERE phone = %s", (request.phone,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="手机号已注册")
            
            if request.email:
                cur.execute("SELECT id FROM users WHERE email = %s", (request.email,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="邮箱已注册")
            
            # 创建用户
            user_code = generate_user_code()
            password_hash = get_password_hash(request.password)
            
            cur.execute(
                """
                INSERT INTO users (user_code, phone, email, password_hash, nickname, gender)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_code,
                    request.phone,
                    request.email,
                    password_hash,
                    request.nickname,
                    request.gender
                )
            )
            user_id = cur.fetchone()[0]
            conn.commit()
    
    # 生成 token
    access_token = create_access_token(data={"sub": str(user_id)})
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserResponse(
            id=user_id,
            user_code=user_code,
            phone=request.phone,
            email=request.email,
            nickname=request.nickname,
            gender=request.gender,
            birth_date=None,
            birth_time=None,
            birth_location=None,
            preferred_city=None,
            avatar_url=None,
            bazi=None,
            xiyong_elements=None
        )
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录",
             dependencies=[Depends(auth_rate_limit)])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    用户登录
    
    **源码位置**: `apps/api/routers/auth.py:login()` (第234行起)
    
    **核心逻辑**:
    1. 根据 username(手机号/邮箱)查询用户
    2. 验证密码哈希
    3. 更新最后登录时间
    4. 生成 JWT token 返回
    
    - username: 手机号或邮箱
    - password: 密码
    """
    import time
    start_time = time.time()
    
    username = form_data.username
    password = form_data.password
    
    # 查询用户
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            # 尝试用手机号或邮箱查找
            cur.execute(
                """
                SELECT id, user_code, phone, email, password_hash, nickname, 
                       gender, birth_date, birth_time, birth_location, preferred_city,
                       avatar_url, bazi, xiyong_elements, is_active
                FROM users 
                WHERE phone = %s OR email = %s
                """,
                (username, username)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=401,
                    detail="用户名或密码错误"
                )
            
            user_id, user_code, phone, email, password_hash, nickname, gender, birth_date, birth_time, birth_location, preferred_city, avatar_url, bazi, xiyong, is_active = row
            
            # 敏感字段解密（兼容明文历史数据）
            birth_date = decrypt_date(birth_date)
            birth_time = decrypt_time(birth_time)
            birth_location = decrypt_pii(birth_location)
            
            if not is_active:
                raise HTTPException(status_code=401, detail="账户已禁用")
            
            if not verify_password(password, password_hash):
                raise HTTPException(
                    status_code=401,
                    detail="用户名或密码错误"
                )
            
            # 更新最后登录时间
            cur.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = %s",
                (user_id,)
            )
            conn.commit()
    
    # 生成 token
    access_token = create_access_token(data={"sub": str(user_id)})
    
    elapsed = time.time() - start_time
    logger.info(f"登录完成: {username}, 耗时: {elapsed:.3f}s")
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserResponse(
            id=user_id,
            user_code=user_code,
            phone=phone,
            email=email,
            nickname=nickname,
            gender=gender,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_location=birth_location,
            preferred_city=preferred_city,
            avatar_url=avatar_url,
            bazi=bazi,
            xiyong_elements=xiyong
        )
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    获取当前登录用户信息
    
    **源码位置**: `apps/api/routers/auth.py:get_me()` (第366行起)
    
    **核心逻辑**: 直接返回当前登录用户的基本信息
    
    **依赖**: `get_current_user()` - 从 JWT token 解析用户信息
    """
    return UserResponse(**current_user)


@router.post("/bazi", response_model=UserResponse, summary="更新用户八字")
async def update_bazi(
    request: UpdateBaziRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    更新用户八字信息
    
    **源码位置**: `apps/api/routers/auth.py:update_bazi()` (第372行起)
    
    **核心逻辑**:
    1. 调用 `packages/utils/bazi_calculator.py:calculate_bazi()` 计算八字
    2. 将八字结果和喜用神保存到数据库
    3. 返回更新后的用户信息
    
    **依赖**:
    - `get_current_user()` - JWT 认证
    - `calculate_bazi()` - 八字计算工具
    """
    from packages.utils.bazi_calculator import calculate_bazi
    
    # PIPL：出生信息属敏感个人信息，需单独同意
    if not request.sensitive_consent:
        raise HTTPException(
            status_code=400,
            detail="请先同意将出生信息用于八字分析（敏感个人信息处理同意）"
        )
    
    # 计算八字
    bazi_result = calculate_bazi(
        request.birth_year,
        request.birth_month,
        request.birth_day,
        request.birth_hour,
        request.gender
    )
    
    # 更新数据库
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users 
                SET birth_date = %s, 
                    birth_time = %s,
                    gender = %s,
                    bazi = %s,
                    xiyong_elements = %s,
                    privacy_agreed_at = COALESCE(privacy_agreed_at, NOW())
                WHERE id = %s
                """,
                (
                    encrypt_pii(f"{request.birth_year}-{request.birth_month:02d}-{request.birth_day:02d}"),
                    encrypt_pii(f"{request.birth_hour:02d}:00:00"),
                    request.gender,
                    bazi_result,
                    bazi_result["suggested_elements"],
                    current_user["id"]
                )
            )
            conn.commit()
    
    # 返回更新后的用户信息
    return UserResponse(
        **{**current_user, 
           "bazi": bazi_result,
           "xiyong_elements": bazi_result["suggested_elements"]}
    )


@router.post("/logout", summary="用户登出")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    用户登出
    
    **源码位置**: `apps/api/routers/auth.py:logout()` (第488行起)
    
    **核心逻辑**: 仅返回成功消息，前端需清除本地 token
    
    **注意**: 当前实现为无状态登出，token 在过期前仍有效
    """
    return {"message": "登出成功"}


@router.get("/profile", response_model=UserProfileResponse, summary="获取用户完整资料")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户的完整资料信息
    
    **源码位置**: `apps/api/routers/auth.py:get_profile()` (第498行起)
    
    **核心逻辑**: 从数据库查询用户完整资料（包含八字、喜用神等）
    
    **与 `/me` 的区别**: 此接口返回更完整的资料，包括创建时间、更新时间
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_code, phone, email, nickname, gender,
                       birth_date, birth_time, birth_location, preferred_city,
                       avatar_url, bazi, xiyong_elements, created_at, updated_at,
                       skin_tone, style_preference, body_type, aesthetic_tags
                FROM users WHERE id = %s
                """,
                (current_user["id"],)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 解析 aesthetic_tags JSONB
            aesthetic_tags = row[17]
            if isinstance(aesthetic_tags, str):
                try:
                    aesthetic_tags = json.loads(aesthetic_tags)
                except Exception:
                    aesthetic_tags = []
            
            return {
                "id": current_user["id"],
                "user_code": row[0],
                "phone": row[1],
                "email": row[2],
                "nickname": row[3],
                "gender": row[4],
                "birth_date": decrypt_date(row[5]),
                "birth_time": decrypt_time(row[6]),
                "birth_location": decrypt_pii(row[7]),
                "preferred_city": row[8],
                "avatar_url": row[9],
                "bazi": row[10],
                "xiyong_elements": row[11],
                "created_at": row[12],
                "updated_at": row[13],
                "skin_tone": row[14],
                "style_preference": row[15],
                "body_type": row[16],
                "aesthetic_tags": aesthetic_tags or [],
            }


@router.patch("/profile", response_model=UserProfileResponse, summary="更新用户资料")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    更新用户资料信息
    
    **源码位置**: `apps/api/routers/auth.py:update_profile()` (第475行起)
    
    **核心逻辑**:
    1. 构建动态 UPDATE SQL（只更新传入的字段）
    2. 如果更新了出生信息，自动调用 `calculate_bazi()` 计算八字
    3. 保存八字结果和喜用神到数据库
    4. 返回更新后的完整资料
    
    **自动八字计算条件**: birth_date、birth_time、gender 同时存在且完整
    
    **依赖**:
    - `get_current_user()` - JWT 认证
    - `calculate_bazi()` - 八字计算
    """
    # 构建更新SQL
    update_fields = []
    params = []
    
    # PIPL：更新出生信息（敏感个人信息）需单独同意
    touches_sensitive = (
        request.birth_date is not None
        or request.birth_time is not None
        or request.birth_location is not None
    )
    if touches_sensitive and not request.sensitive_consent:
        raise HTTPException(
            status_code=400,
            detail="请先同意将出生信息用于八字分析（敏感个人信息处理同意）"
        )
    if touches_sensitive:
        update_fields.append("privacy_agreed_at = COALESCE(privacy_agreed_at, NOW())")
    
    if request.nickname is not None:
        update_fields.append("nickname = %s")
        params.append(request.nickname)
    
    if request.gender is not None:
        update_fields.append("gender = %s")
        params.append(request.gender)
    
    if request.birth_date is not None:
        update_fields.append("birth_date = %s")
        params.append(encrypt_pii(request.birth_date))
    
    if request.birth_time is not None:
        update_fields.append("birth_time = %s")
        params.append(encrypt_pii(request.birth_time))
    
    if request.birth_location is not None:
        update_fields.append("birth_location = %s")
        params.append(encrypt_pii(request.birth_location))
    
    if request.preferred_city is not None:
        update_fields.append("preferred_city = %s")
        params.append(request.preferred_city)
    
    if request.avatar_url is not None:
        update_fields.append("avatar_url = %s")
        params.append(request.avatar_url)
    
    # Week 4: 审美画像字段
    if request.skin_tone is not None:
        update_fields.append("skin_tone = %s")
        params.append(request.skin_tone)
    
    if request.style_preference is not None:
        update_fields.append("style_preference = %s")
        params.append(request.style_preference)
    
    if request.body_type is not None:
        update_fields.append("body_type = %s")
        params.append(request.body_type)
    
    if request.aesthetic_tags is not None:
        update_fields.append("aesthetic_tags = %s")
        params.append(json.dumps(request.aesthetic_tags))
        update_fields.append("aesthetic_updated_at = NOW()")
    
    # 检查是否需要重新计算八字（出生日期或时间有更新）
    needs_bazi_update = request.birth_date is not None or request.birth_time is not None
    bazi_data = None
    xiyong_data = None
    
    if needs_bazi_update:
        # 获取完整的出生信息（使用新值或数据库现有值）
        birth_date = request.birth_date or current_user.get("birth_date")
        birth_time = request.birth_time or current_user.get("birth_time")
        gender = request.gender or current_user.get("gender")
        
        if birth_date and birth_time and gender:
            try:
                # 解析日期和时间
                birth_date_obj = birth_date if isinstance(birth_date, date) else datetime.strptime(birth_date, "%Y-%m-%d").date()
                birth_time_obj = birth_time if isinstance(birth_time, time) else datetime.strptime(str(birth_time), "%H:%M:%S").time() if isinstance(birth_time, str) and ":" in str(birth_time) else datetime.strptime(str(birth_time), "%H:%M").time()
                
                # 计算八字
                bazi_result = calculate_bazi(
                    birth_year=birth_date_obj.year,
                    birth_month=birth_date_obj.month,
                    birth_day=birth_date_obj.day,
                    birth_hour=birth_time_obj.hour,
                    gender=gender
                )
                
                # calculate_bazi 直接返回完整结果，suggested_elements 就是喜用神
                bazi_data = bazi_result
                xiyong_data = bazi_result.get("suggested_elements", [])
                
                # 添加八字字段到更新列表
                update_fields.append("bazi = %s")
                params.append(json.dumps(bazi_data, ensure_ascii=False))
                update_fields.append("xiyong_elements = %s")
                params.append(json.dumps(xiyong_data, ensure_ascii=False))
                
                logger.info(f"用户 {current_user['id']} 八字自动计算完成")
                
            except Exception as e:
                logger.error(f"八字计算失败: {e}")
                # 八字计算失败不影响其他资料更新
    
    # 如果没有要更新的字段
    if not update_fields:
        # 返回当前用户信息
        return await get_profile(current_user)
    
    # 添加更新时间和用户ID
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(current_user["id"])
    
    # 执行更新
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            sql = f"""
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            cur.execute(sql, params)
            conn.commit()
    
    # 返回更新后的信息
    return await get_profile(current_user)


@router.delete("/profile", status_code=204, summary="删除账户")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """
    删除用户账户（软删除）
    
    **源码位置**: `apps/api/routers/auth.py:delete_account()` (第590行起)
    
    **核心逻辑**: 软删除，将 `is_active` 设为 FALSE
    
    **注意**: 用户数据保留，仅标记为 inactive；彻底注销请用 DELETE /account
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (current_user["id"],)
            )
            conn.commit()


@router.delete("/account", status_code=204, summary="注销账号（彻底删除）")
async def deregister_account(current_user: dict = Depends(get_current_user)):
    """
    注销账号：彻底删除用户及全部个人数据（PIPL 合规要求）
    
    **核心逻辑**:
    1. 收集用户上传的图片 URL（自定义衣橱物品 + 头像）
    2. 删除 users 行，业务表由外键 ON DELETE CASCADE 自动级联删除；
       user_disliked_items 无外键约束，需显式删除
    3. 事务提交后 best-effort 清理对象存储中的图片
    
    **注意**: 操作不可逆，前端应做二次确认
    """
    user_id = current_user["id"]
    image_urls: List[str] = []

    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 收集需清理的图片：用户自定义衣橱物品 + 头像
            cur.execute(
                "SELECT image_url FROM user_wardrobe WHERE user_id = %s AND is_custom = TRUE AND image_url IS NOT NULL",
                (user_id,)
            )
            image_urls = [row[0] for row in cur.fetchall() if row and row[0]]
            if current_user.get("avatar_url"):
                image_urls.append(current_user["avatar_url"])

            # 2. 删除无外键约束的关联表，再删除用户（其余表 CASCADE）
            cur.execute("DELETE FROM user_disliked_items WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()

    # 3. 清理对象存储图片（best-effort，失败不影响注销结果）
    try:
        from apps.api.services.storage import get_storage_service
        storage = get_storage_service()
        if storage.available:
            for url in image_urls:
                try:
                    storage.delete_file(url)
                    thumb = storage.get_thumbnail_url(url)
                    if thumb and thumb != url:
                        storage.delete_file(thumb)
                except Exception as e:
                    logger.warning(f"注销清理图片失败 {url}: {e}")
    except Exception as e:
        logger.warning(f"注销后存储清理异常: {e}")

    logger.info(f"用户 {user_id} 已注销，清理图片 {len(image_urls)} 张")
