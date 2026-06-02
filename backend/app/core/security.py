from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 密码哈希工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码进行哈希"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码是否匹配"""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """生成 JWT 访问令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """解码并验证 JWT，失败时抛出 JWTError"""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
