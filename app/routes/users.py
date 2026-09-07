from flask import request
from flask_restx import Namespace, Resource, fields
from app.extensions import db, bcrypt
from app.models.user import User
from app.models.role import Role
from app.services.auth_service import token_required
from http import HTTPStatus

# 네임스페이스 생성
users_ns = Namespace('users', description='사용자 관리 API')

# --- [Swagger 데이터 모델 정의] ---

register_model = users_ns.model('UserRegisterInput', {
    'email': fields.String(required=True, description='이메일', example='newuser@test.com'),
    'password': fields.String(required=True, description='비밀번호', example='supersecret123'),
    'name': fields.String(required=True, description='이름', example='신입연구원'),
    'role_name': fields.String(description='직급 (기본값: ROLE_USER)', example='ROLE_USER')
})

user_update_model = users_ns.model('UserUpdateInput', {
    'name': fields.String(description='변경할 이름', example='수석연구원'),
    'password': fields.String(description='변경할 비밀번호', example='newsecret123'),
    'role_name': fields.String(description='변경할 직급', example='ROLE_ADMIN')
})


# --- [API 리소스 정의] ---

@users_ns.route('/')
class UserList(Resource):

    @users_ns.doc(
        description='등록된 사용자 목록을 조회합니다.\n\n'
                    '- 레벨 1(최고관리자): 모든 계정 조회 가능\n'
                    '- 레벨 2(관리자): 일반 사용자(레벨 3)만 조회 가능\n'
                    '- 레벨 3(일반 유저): 접근 불가',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user):
        """사용자 목록 조회 (권한 레벨 기반 차등 조회)"""
        current_level = current_user.role_info.level if current_user.role_info else 3

        # 일반 유저(레벨 3)는 조회 불가
        if current_level > 2:
            return {"error": "접근 거부: 사용자 목록 조회는 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        if current_level == 1:
            # 최고관리자: 모든 계정 조회
            users = User.query.all()
        else:
            # 관리자(레벨 2): 일반 사용자(레벨 3)만 조회
            user_role = Role.query.filter_by(role_name='ROLE_USER').first()
            if user_role:
                users = User.query.filter_by(role_id=user_role.id).all()
            else:
                users = []

        return [u.to_dict() for u in users], HTTPStatus.OK


@users_ns.route('/register')
class UserRegister(Resource):

    @users_ns.expect(register_model)
    @users_ns.doc(
        description='새로운 사용자를 등록합니다.\n\n'
                    '- 레벨 2(관리자): 레벨 3(일반유저)만 생성 가능\n'
                    '- 레벨 1(최고관리자): 레벨 2~3 생성 가능\n'
                    '- API로 최고관리자(레벨 1)는 생성 불가',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def post(self, current_user):
        """새로운 사용자 등록 (권한 레벨 기반 차등 생성)"""
        current_level = current_user.role_info.level if current_user.role_info else 3

        # 일반 유저(레벨 3)는 계정 생성 불가
        if current_level > 2:
            return {"error": "접근 거부: 일반 유저는 계정을 생성할 수 없습니다."}, HTTPStatus.FORBIDDEN

        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        role_name = data.get('role_name', 'ROLE_USER')

        if not email or not password or not name:
            return {"error": "이메일, 비밀번호, 이름을 모두 입력해주세요."}, HTTPStatus.BAD_REQUEST

        if User.query.filter_by(email=email).first():
            return {"error": "이미 등록된 이메일입니다."}, HTTPStatus.CONFLICT

        # 직급 확인
        target_role = Role.query.filter_by(role_name=role_name).first()
        if not target_role:
            return {"error": f"'{role_name}'(은)는 존재하지 않는 직급입니다."}, HTTPStatus.BAD_REQUEST

        # API로 최고관리자(레벨 1)는 생성 불가
        if target_role.level == 1:
            return {"error": "보안 위반: 최고관리자 계정은 API를 통해 생성할 수 없습니다."}, HTTPStatus.FORBIDDEN

        # 나보다 높거나 같은 등급은 생성 불가 (낮은 숫자 = 높은 권한)
        if current_level >= target_role.level:
            return {"error": f"접근 거부: 본인(레벨 {current_level})보다 높거나 같은 등급(레벨 {target_role.level})은 생성할 수 없습니다."}, HTTPStatus.FORBIDDEN

        # 새 유저 생성 (loginServer의 Bcrypt 암호화 사용)
        new_user = User(
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            name=name,
            role_id=target_role.id
        )

        db.session.add(new_user)
        db.session.commit()

        return {"message": f"{name}님 환영합니다! {target_role.description} 권한으로 가입되었습니다."}, HTTPStatus.CREATED


@users_ns.route('/<int:user_id>')
@users_ns.param('user_id', '수정/삭제할 유저의 고유 ID 번호')
class UserDetail(Resource):

    @users_ns.expect(user_update_model)
    @users_ns.doc(
        description='특정 유저의 정보를 수정합니다. (최고관리자 레벨 1 전용)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def put(self, current_user, user_id):
        """특정 유저 정보 수정 (최고관리자 레벨 1 전용)"""
        current_level = current_user.role_info.level if current_user.role_info else 3

        if current_level > 1:
            return {"error": "접근 거부: 유저 정보 수정은 최고관리자(레벨 1)만 가능합니다."}, HTTPStatus.FORBIDDEN

        target_user = User.query.get_or_404(user_id)
        data = request.get_json()

        if 'name' in data:
            target_user.name = data['name']
        if 'password' in data:
            target_user.password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        if 'role_name' in data:
            new_role = Role.query.filter_by(role_name=data['role_name']).first()
            if not new_role:
                return {"error": f"'{data['role_name']}'(은)는 존재하지 않는 직급입니다."}, HTTPStatus.BAD_REQUEST
            if new_role.level == 1:
                return {"error": "보안 위반: 일반 계정을 최고관리자로 승급시킬 수 없습니다."}, HTTPStatus.FORBIDDEN
            target_user.role_id = new_role.id

        db.session.commit()
        return {"message": f"[{target_user.email}] 계정의 정보가 성공적으로 수정되었습니다."}, HTTPStatus.OK

    @users_ns.doc(
        description='특정 유저를 시스템에서 삭제합니다. (최고관리자 레벨 1 전용)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def delete(self, current_user, user_id):
        """특정 유저 삭제 (최고관리자 레벨 1 전용)"""
        current_level = current_user.role_info.level if current_user.role_info else 3

        if current_level > 1:
            return {"error": "접근 거부: 유저 삭제는 최고관리자(레벨 1)만 가능합니다."}, HTTPStatus.FORBIDDEN

        target_user = User.query.get_or_404(user_id)

        # 자폭 방지: 최고관리자가 자기 자신을 삭제하는 것을 방지
        if current_user.id == target_user.id:
            return {"error": "보안 위반: 현재 로그인된 최고관리자 본인의 계정은 삭제할 수 없습니다."}, HTTPStatus.BAD_REQUEST

        db.session.delete(target_user)
        db.session.commit()

        return {"message": f"유저({target_user.email})가 시스템에서 완전히 삭제되었습니다."}, HTTPStatus.OK
