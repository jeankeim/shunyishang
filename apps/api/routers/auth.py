"""
用户认证路由模块
提供注册、登录、用户信息管理
"""

import json
import logging
from datetime import timedelta, datetime, date, time
from typing import Optional

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
from packages.utils.bazi_calculator import calculate_bazi

router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ========== 请求/响应模型 ==========

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    nickname: Optional[str] = Field(None, description="昵称")
    gender: Optional[str] = Field(None, pattern="^(男|女)?$", description="性别")


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


class UpdateProfileRequest(BaseModel):
    """更新用户资料请求"""
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    gender: Optional[str] = Field(None, pattern="^(男|女)?$", description="性别")
    birth_date: Optional[date] = Field(None, description="出生日期")
    birth_time: Optional[time] = Field(None, description="出生时间")
    birth_location: Optional[str] = Field(None, max_length=200, description="出生地点")
    preferred_city: Optional[str] = Field(None, max_length=100, description="常驻城市")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")


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
                "birth_date": row[6],
                "birth_time": row[7],
                "birth_location": row[8],
                "preferred_city": row[9],
                "avatar_url": row[10],
                "bazi": row[11],
                "xiyong_elements": row[12],
            }


# ========== 路由 ==========

@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(request: UserRegisterRequest):
    """
    用户注册
    
    手机号或邮箱至少提供一个
    
    **源码位置**: `apps/api/routers/auth.py:register()` (第168行起)
    
    **核心逻辑**:
    1. 检查手机号/邮箱是否已注册
    2. 生成 user_code 和密码哈希
    3. 插入用户数据到数据库
    4. 生成 JWT token 返回
    
    **请求示例**:
    ```json
    {
        "phone": "13800138000",
        "password": "123456",
        "nickname": "张三",
        "gender": "男"
    }
    ```
    """
    if not request.phone and not request.email:
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
            bazi=None,
            xiyong_elements=None
        )
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
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
                    xiyong_elements = %s
                WHERE id = %s
                """,
                (
                    f"{request.birth_year}-{request.birth_month:02d}-{request.birth_day:02d}",
                    f"{request.birth_hour:02d}:00:00",
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
                       avatar_url, bazi, xiyong_elements, created_at, updated_at
                FROM users WHERE id = %s
                """,
                (current_user["id"],)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            return {
                "id": current_user["id"],
                "user_code": row[0],
                "phone": row[1],
                "email": row[2],
                "nickname": row[3],
                "gender": row[4],
                "birth_date": row[5],
                "birth_time": row[6],
                "birth_location": row[7],
                "preferred_city": row[8],
                "avatar_url": row[9],
                "bazi": row[10],
                "xiyong_elements": row[11],
                "created_at": row[12],
                "updated_at": row[13]
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
    
    if request.nickname is not None:
        update_fields.append("nickname = %s")
        params.append(request.nickname)
    
    if request.gender is not None:
        update_fields.append("gender = %s")
        params.append(request.gender)
    
    if request.birth_date is not None:
        update_fields.append("birth_date = %s")
        params.append(request.birth_date)
    
    if request.birth_time is not None:
        update_fields.append("birth_time = %s")
        params.append(request.birth_time)
    
    if request.birth_location is not None:
        update_fields.append("birth_location = %s")
        params.append(request.birth_location)
    
    if request.preferred_city is not None:
        update_fields.append("preferred_city = %s")
        params.append(request.preferred_city)
    
    if request.avatar_url is not None:
        update_fields.append("avatar_url = %s")
        params.append(request.avatar_url)
    
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
    
    **注意**: 用户数据保留，仅标记为 inactive
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (current_user["id"],)
            )
            conn.commit()
