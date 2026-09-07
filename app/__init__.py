import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from app.extensions import bcrypt, db, api, redis_client
import app.extensions as extensions
from app.routes.auth import auth_ns
from app.routes.devices import devices_ns
from app.routes.users import users_ns
from app.routes.buildings import building_ns, defect_ns
from app.routes.safety_grades import grade_ns
from app.routes.device_states import device_state_ns
from app.routes.uploads import upload_ns

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.url_map.strict_slashes = False  # /api/devices와 /api/devices/ 모두 허용 (308 방지)

    # 한글 유니코드 변환 방지
    app.json.ensure_ascii = False

    # 확장 초기화
    db.init_app(app)
    bcrypt.init_app(app)
    api.init_app(app)
    CORS(app)  # 외부 IP에서 API 호출 허용

    # Redis 초기화 (토큰 블랙리스트 & 세션 관리)
    import redis
    extensions.redis_client = redis.Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB'],
        decode_responses=True
    )
    try:
        extensions.redis_client.ping()
        print("[시스템] Redis 연결 성공")
    except redis.ConnectionError:
        print("[경고] Redis 연결 실패 - 토큰 블랙리스트 기능이 비활성화됩니다.")
        extensions.redis_client = None

    # 네임스페이스 등록
    api.add_namespace(auth_ns, path='/api/auth')
    api.add_namespace(devices_ns, path='/api/devices')
    api.add_namespace(users_ns, path='/api/users')
    api.add_namespace(building_ns, path='/api/buildings')
    api.add_namespace(defect_ns, path='/api/defects')
    api.add_namespace(grade_ns, path='/api/safety-grades')
    api.add_namespace(device_state_ns, path='/api/device-states')
    api.add_namespace(upload_ns, path='/api/upload')

    # DB 모델 임포트 및 테이블 자동 생성
    with app.app_context():
        from app.models.role import Role
        from app.models.user import User
        from app.models.device import JetsonDevice
        from app.models.building import Building, Defect
        from app.models.risk_assessment import RiskAssessment, Alert
        from app.models.device_state import DeviceState
        from app.models.safety_grade import SafetyGrade
        db.create_all()

    # 기본 루트 경로 (접속 확인용)
    @app.route('/')
    def index():
        # 서버 공인 IP는 환경변수에서 불러온다. 코드에 하드코딩하지 않는다.
        return jsonify({
            "status": "online",
            "message": "Safe Guard AI Server is running!",
            "public_ip": os.getenv("SERVER_PUBLIC_IP", "")
        }), 200

    # 모든 요청에 대해 로그를 남김 (디버깅용)
    @app.before_request
    def log_request_info():
        print(f"--- [REQUEST] {request.method} {request.url} ---")
        print(f"Headers: {dict(request.headers)}")
        if request.is_json:
            # silent=True를 설정하여 바디가 비어있어도 400 에러를 던지지 않도록 수정
            body = request.get_json(silent=True)
            if body:
                print(f"Body: {body}")
        print("---------------------------------------")

    return app

