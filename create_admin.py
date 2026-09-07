# create_admin.py — 최고관리자 계정 초기 생성 스크립트
import os
from dotenv import load_dotenv
from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User
from app.models.role import Role

# .env 파일 로드 (관리자 계정 정보)
load_dotenv()

app = create_app()


def setup_initial_data():
    with app.app_context():
        # 1. 테이블이 없다면 생성
        db.create_all()

        # 2. 3가지 기본 직급(Role) 세팅
        roles_data = [
            {"name": "ROLE_SUPER_ADMIN", "desc": "시스템 최고 관리자 (모든 권한)", "level": 1},
            {"name": "ROLE_ADMIN", "desc": "현장 관리자 (기기 등록/수정)", "level": 2},
            {"name": "ROLE_USER", "desc": "일반 모니터링 요원 (조회 전용)", "level": 3}
        ]

        for r_data in roles_data:
            role = Role.query.filter_by(role_name=r_data["name"]).first()
            if not role:
                new_role = Role(role_name=r_data["name"], description=r_data["desc"], level=r_data["level"])
                db.session.add(new_role)
                print(f"직급 생성됨: {r_data['name']}")

        db.session.commit()

        # 3. 최초의 최고관리자 계정 생성 (Bcrypt 암호화 사용)
        # 계정 정보는 환경변수(.env)에서 불러온다. 코드에 하드코딩하지 않는다.
        super_admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
        super_admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "changeme")
        existing_admin = User.query.filter_by(email=super_admin_email).first()

        if not existing_admin:
            super_role = Role.query.filter_by(role_name="ROLE_SUPER_ADMIN").first()

            super_admin = User(
                email=super_admin_email,
                password_hash=bcrypt.generate_password_hash(super_admin_password).decode('utf-8'),
                name="최고관리자",
                role_id=super_role.id
            )
            db.session.add(super_admin)
            db.session.commit()
            print(f"[완료] 최고관리자 계정( {super_admin_email} )이 성공적으로 생성되었습니다!")
        else:
            print("[경고] 이미 최고관리자 계정이 존재합니다.")


if __name__ == "__main__":
    setup_initial_data()
