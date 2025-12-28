from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from infrastructure.config.settings import settings
import bcrypt

# bcrypt를 직접 사용하도록 설정 (passlib의 초기화 문제 회피)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")

SECRET_KEY = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증 (bcrypt는 최대 72바이트까지만 지원)"""
    # 비밀번호를 바이트로 변환하고 72바이트로 제한
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        # UTF-8 continuation byte 제거
        while password_bytes and (password_bytes[-1] & 0b11000000) == 0b10000000:
            password_bytes = password_bytes[:-1]
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    
    # bcrypt 직접 사용
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        # fallback to passlib
        return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해시화 (bcrypt는 최대 72바이트까지만 지원)"""
    # bcrypt는 72바이트 제한이 있으므로, 비밀번호를 바이트로 변환하고 72바이트로 제한
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # 72바이트로 자르기
        password_bytes = password_bytes[:72]
        # 잘린 바이트가 유효한 UTF-8 문자가 아닐 수 있으므로 처리
        # UTF-8 continuation byte (0x80-0xBF)를 제거
        while password_bytes and (password_bytes[-1] & 0b11000000) == 0b10000000:
            password_bytes = password_bytes[:-1]
        # 바이트를 다시 문자열로 변환
        try:
            password = password_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # 디코딩 실패 시 errors='ignore'로 처리
            password = password_bytes.decode('utf-8', errors='ignore')
        # 다시 바이트로 변환 (72바이트 이하로 보장됨)
        password_bytes = password.encode('utf-8')
    
    # bcrypt 직접 사용 (passlib의 초기화 문제 회피)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """JWT 토큰 디코딩"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

