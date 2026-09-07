import jwt
import datetime
from functools import wraps
from flask import current_app, request
from app.extensions import db, bcrypt
from app.models.user import User
from app.models.role import Role


def token_required(f):
    """JWT Access Token 검증 데코레이터.
    인증된 사용자 객체를 current_user로 주입합니다."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return {"error": "토큰이 필요합니다."}, 401

        try:
            # "Bearer <token>" 형식에서 토큰 추출
            token = auth_header.split(" ")[1] if " " in auth_header else auth_header
            if not token:
                return {"error": "토큰이 비어있습니다."}, 401
        except IndexError:
            return {"error": "유효하지 않은 토큰 형식입니다."}, 401

        # Redis 블랙리스트 확인 (로그아웃된 토큰 차단)
        if AuthService.is_token_blacklisted(token):
            return {"error": "로그아웃된 토큰입니다. 다시 로그인해주세요."}, 401

        payload, error = AuthService.decode_token(token)
        if error:
            return {"error": error}, 401

        current_user = User.query.get(payload['user_id'])
        if not current_user:
            return {"error": "사용자를 찾을 수 없습니다."}, 401

        return f(*args, current_user=current_user, **kwargs)
    return decorated


class AuthService:
    # ==========================================
    # Redis 토큰 관리 메서드
    # ==========================================

    @staticmethod
    def _get_redis():
        """Redis 클라이언트를 안전하게 가져오기 (None이면 Redis 미연결 상태)"""
        import app.extensions as extensions
        return extensions.redis_client

    @staticmethod
    def store_refresh_token(user_id, refresh_token):
        """Refresh Token을 Redis에 저장 (TTL = Refresh Token 만료 시간)"""
        redis_conn = AuthService._get_redis()
        if redis_conn is None:
            return

        expires = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', 1800)
        # Key: refresh:{user_id}, Value: refresh_token, TTL: 만료 시간
        redis_conn.setex(f"refresh:{user_id}", expires, refresh_token)

    @staticmethod
    def revoke_refresh_token(user_id):
        """해당 유저의 Refresh Token을 Redis에서 삭제 (로그아웃/강제 만료)"""
        redis_conn = AuthService._get_redis()
        if redis_conn is None:
            return

        redis_conn.delete(f"refresh:{user_id}")

    @staticmethod
    def is_refresh_token_valid(user_id, refresh_token):
        """Redis에 저장된 Refresh Token과 일치하는지 확인"""
        redis_conn = AuthService._get_redis()
        if redis_conn is None:
            return True  # Redis 미연결 시 기존 JWT 검증만 사용

        stored_token = redis_conn.get(f"refresh:{user_id}")
        if not stored_token:
            return False  # Redis에 없으면 만료/로그아웃된 토큰
        return stored_token == refresh_token

    @staticmethod
    def blacklist_access_token(token):
        """Access Token을 블랙리스트에 등록 (남은 만료 시간만큼 TTL 설정)"""
        redis_conn = AuthService._get_redis()
        if redis_conn is None:
            return

        try:
            # 토큰에서 만료 시간 추출
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            exp = datetime.datetime.utcfromtimestamp(payload['exp'])
            remaining = (exp - datetime.datetime.utcnow()).total_seconds()

            if remaining > 0:
                # Key: blacklist:{token}, TTL: 남은 만료 시간
                redis_conn.setex(f"blacklist:{token}", int(remaining), "revoked")
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass  # 이미 만료된 토큰은 블랙리스트 불필요

    @staticmethod
    def is_token_blacklisted(token):
        """토큰이 블랙리스트에 있는지 확인"""
        redis_conn = AuthService._get_redis()
        if redis_conn is None:
            return False  # Redis 미연결 시 블랙리스트 비활성화

        return redis_conn.exists(f"blacklist:{token}") > 0

    # ==========================================
    # 기존 인증 메서드 (Redis 연동 추가)
    # ==========================================

    @staticmethod
    def register(email, password, name, role_id=3):
        # 이미 존재하는 이메일인지 확인
        if User.query.filter_by(email=email).first():
            return False, "이미 존재하는 이메일입니다."

        # role_id 유효성 확인
        role = Role.query.get(role_id)
        if not role:
            return False, f"role_id={role_id}에 해당하는 직급이 존재하지 않습니다."

        # 새 유저 생성 및 DB에 저장
        new_user = User(
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            name=name,
            role_id=role_id
        )
        db.session.add(new_user)
        db.session.commit()
        return True, None

    @staticmethod
    def _create_access_token(user):
        """Access Token 생성 (5분 만료) — role/level 정보 포함"""
        expires = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 300)

        # 사용자의 직급/레벨 정보 가져오기
        role_name = user.role_info.role_name if user.role_info else "ROLE_USER"
        role_level = user.role_info.level if user.role_info else 3

        payload = {
            'user_id': user.id,
            'email': user.email,
            'role': role_name,
            'level': role_level,
            'type': 'access',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=expires)
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def _create_refresh_token(user):
        """Refresh Token 생성 (30분 만료)"""
        expires = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', 1800)
        payload = {
            'user_id': user.id,
            'email': user.email,
            'type': 'refresh',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=expires)
        }
        return jwt.encode(payload, current_app.config['JWT_REFRESH_SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def login(email, password):
        user = User.query.filter_by(email=email).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            return None, "이메일 또는 비밀번호가 올바르지 않습니다."

        # Access Token + Refresh Token 동시 발급
        access_token = AuthService._create_access_token(user)
        refresh_token = AuthService._create_refresh_token(user)

        # Refresh Token을 Redis에 저장
        AuthService.store_refresh_token(user.id, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        }, None

    @staticmethod
    def logout(access_token, refresh_token=None):
        """로그아웃 처리: Access Token 블랙리스트 등록 + Refresh Token 폐기"""
        # Access Token을 블랙리스트에 등록
        AuthService.blacklist_access_token(access_token)

        # Refresh Token에서 user_id 추출하여 Redis에서 삭제
        if refresh_token:
            payload, _ = AuthService.decode_refresh_token(refresh_token)
            if payload:
                AuthService.revoke_refresh_token(payload['user_id'])

    @staticmethod
    def refresh_access_token(refresh_token_str, extend=False):
        """
        Refresh Token으로 새 Access Token 발급.

        Args:
            refresh_token_str: 클라이언트가 보낸 refresh token 문자열
            extend: True이면 refresh token도 새로 발급 (30분 리셋)

        Returns:
            (result_dict, error_message)
        """
        # Refresh Token 검증
        payload, error = AuthService.decode_refresh_token(refresh_token_str)
        if error:
            return None, error

        # 토큰 타입 검증
        if payload.get('type') != 'refresh':
            return None, "유효하지 않은 토큰 타입입니다."

        # Redis에서 Refresh Token 유효성 확인
        user_id = payload['user_id']
        if not AuthService.is_refresh_token_valid(user_id, refresh_token_str):
            return None, "폐기된 토큰입니다. 다시 로그인해주세요."

        # 유저 조회
        user = User.query.get(user_id)
        if not user:
            return None, "사용자를 찾을 수 없습니다."

        # 새 Access Token 발급
        result = {
            "access_token": AuthService._create_access_token(user)
        }

        # extend=True이면 Refresh Token도 새로 발급 (Rotation)
        if extend:
            new_refresh = AuthService._create_refresh_token(user)
            result["refresh_token"] = new_refresh
            # Redis에 새 Refresh Token으로 교체 (기존 토큰 자동 폐기)
            AuthService.store_refresh_token(user.id, new_refresh)

        return result, None

    @staticmethod
    def decode_token(token):
        """Access Token을 검증하고 페이로드를 반환"""
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            if payload.get('type') != 'access':
                return None, "유효하지 않은 토큰 타입입니다."
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "토큰이 만료되었습니다."
        except jwt.InvalidTokenError:
            return None, "유효하지 않은 토큰입니다."

    @staticmethod
    def decode_refresh_token(token):
        """Refresh Token을 검증하고 페이로드를 반환"""
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_REFRESH_SECRET_KEY'],
                algorithms=['HS256']
            )
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "리프레시 토큰이 만료되었습니다. 다시 로그인해주세요."
        except jwt.InvalidTokenError:
            return None, "유효하지 않은 리프레시 토큰입니다."
