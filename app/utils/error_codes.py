# --- 공통 에러 코드 정의 ---
# 에러 코드를 한 곳에서 관리하고, 데코레이터로 Swagger에 자동 등록

# 인증(Auth) 관련 에러 코드
AUTH_ERRORS = {
    400: "필수 필드 누락",
    401: "이메일 또는 비밀번호 불일치",
    409: "이미 존재하는 이메일",
    500: "서버 내부 오류",
}

# 토큰(Token) 관련 에러 코드
TOKEN_ERRORS = {
    400: "필수 필드 누락 (refresh_token)",
    401: "토큰 만료 또는 유효하지 않은 토큰",
    500: "서버 내부 오류",
}


def apply_error_responses(namespace, error_dict, error_model):
    """
    에러 응답을 한 번에 Swagger 문서에 등록하는 데코레이터.

    사용법:
        @apply_error_responses(auth_ns, AUTH_ERRORS, error_model)
        def post(self):
            ...
    """
    def decorator(func):
        for code, description in error_dict.items():
            func = namespace.response(code=code, description=description, model=error_model)(func)
        return func
    return decorator
