from functools import wraps
from flask import request, jsonify
from app.services.auth_service import AuthService

def token_required(f):
    """
    보호된 라우트에 사용하는 데코레이터.
    요청 헤더에서 JWT 토큰을 꺼내 검증한 뒤,
    유효하면 현재 유저 정보를 함수에 전달합니다.
    
    사용법:
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify(current_user)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Authorization 헤더에서 토큰 추출 (Bearer <token>)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({"error": "토큰이 없습니다. 로그인해주세요."}), 401

        # 토큰 검증
        payload, error = AuthService.decode_token(token)
        if error:
            return jsonify({"error": error}), 401

        # 검증 성공 시 유저 정보를 함수에 전달
        kwargs['current_user'] = payload
        return f(*args, **kwargs)

    return decorated
