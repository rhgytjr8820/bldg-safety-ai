import os
import threading
import subprocess
import atexit
from dotenv import load_dotenv
from app import create_app

# .env 파일 로드 (관리자 계정 등 초기화에 필요한 환경변수)
load_dotenv()

from app.extensions import db, bcrypt
from app.models.role import Role
from app.models.user import User
from app.services.tcp_server import start_tcp_server
from app.models.risk_assessment import RiskAssessment, Alert
from app.models.device_state import DeviceState
from app.models.safety_grade import SafetyGrade

def stop_mediamtx():
    print("[시스템] MediaMTX (영상 중계 서버)를 종료합니다...")
    subprocess.run(["docker", "stop", "mediamtx_server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_mediamtx():
    print("[시스템] MediaMTX (영상 중계 서버) 도커 컨테이너를 시작합니다...")
    subprocess.run(["docker", "rm", "-f", "mediamtx_server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([
        "docker", "run", "-d", "--rm", "--name", "mediamtx_server",
        "-e", "MTX_RTSPADDRESS=:6380",
        "-p", "6380:6380", "-p", "1935:1935", "-p", "8888:8888", "-p", "8889:8889", "-p", "8189:8189/udp",
        "bluenviron/mediamtx"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    atexit.register(stop_mediamtx)

app = create_app()

if __name__ == '__main__':
    # 서버 켜질 때 영상 중계기도 함께 켬
    start_mediamtx()

    with app.app_context():
        # 1. 3단계 기본 권한(Role)이 없으면 자동 생성
        if not Role.query.first():
            db.session.add(Role(role_name='ROLE_SUPER_ADMIN', description='최고 관리자', level=1))
            db.session.add(Role(role_name='ROLE_ADMIN', description='현장 관리자', level=2))
            db.session.add(Role(role_name='ROLE_USER', description='일반 사용자', level=3))
            db.session.commit()
            print("[시스템] 3단계 기본 권한이 DB에 생성되었습니다.")

        # 2. 최고관리자 계정이 없으면 자동 생성
        # 계정 정보는 환경변수(.env)에서 불러온다. 코드에 하드코딩하지 않는다.
        super_admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
        super_admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "changeme")
        if not User.query.filter_by(email=super_admin_email).first():
            super_role = Role.query.filter_by(role_name="ROLE_SUPER_ADMIN").first()
            if super_role:
                super_admin = User(
                    email=super_admin_email,
                    password_hash=bcrypt.generate_password_hash(super_admin_password).decode('utf-8'),
                    name="최고관리자",
                    role_id=super_role.id
                )
                db.session.add(super_admin)
                db.session.commit()
                print(f"[시스템] 최고관리자 계정({super_admin_email})이 자동 생성되었습니다.")

        # =========================================================
        # 3. 안전등급(SafetyGrade) 기초 데이터 자동 세팅
        # =========================================================
        if SafetyGrade.query.count() == 0:
            grades_data = [
                SafetyGrade(grade='A', label='우수', state='문제없음', description='결함이 없는 최상의 상태'),
                SafetyGrade(grade='B', label='양호', state='경미한 결함', description='보조부재에 경미한 결함이 발생했으나, 기능 발휘에는 지장이 없는 상태'),
                SafetyGrade(grade='C', label='보통', state='주요부재 경미한 결함', description='주요부재에 경미한 결함 또는 보조부재에 광범위한 결함이 발생하여 보수가 필요한 상태'),
                SafetyGrade(grade='D', label='미흡', state='주요부재 노후화/결함', description='주요부재에 결함이 발생하여 긴급한 보수 및 보강이 필요하며 사용제한 여부를 결정해야 하는 상태'),
                SafetyGrade(grade='E', label='불량', state='심각한 결함', description='주요부재에 발생한 심각한 결함으로 시설물 안전에 위험이 있어 즉각 사용을 금지하고 개축해야 하는 상태')
            ]
            db.session.bulk_save_objects(grades_data)
            db.session.commit()
            print("[시스템] 시설물 안전등급(A~E) 초기 데이터 세팅 완료!")

    # TCP 소켓 서버를 백그라운드 스레드로 실행 (포트 5001)
    tcp_thread = threading.Thread(target=start_tcp_server, args=(app,))
    tcp_thread.daemon = True
    tcp_thread.start()

    # Flask 웹 서버 실행 (메인 스레드, 포트 1310)
    # use_reloader=False: 스레드 중복 생성 방지
    app.run(debug=True, host='0.0.0.0', port=1310, use_reloader=False)

