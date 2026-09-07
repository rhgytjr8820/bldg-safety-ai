from flask import request
from flask_restx import Namespace, Resource, fields
from app.extensions import db
from app.models.device import JetsonDevice
from app.services.auth_service import AuthService, token_required
from http import HTTPStatus

# 네임스페이스 생성
devices_ns = Namespace('devices', description='Jetson 기기 관리 API')

# --- [Swagger 데이터 모델 정의] ---

device_register_model = devices_ns.model('DeviceRegister', {
    'mac_address': fields.String(required=True, description='기기 MAC 주소', example='AA:BB:CC:DD:EE:11'),
    'device_name': fields.String(required=True, description='기기 이름', example='1공장 정문 카메라'),
    'location': fields.String(description='설치 위치', example='부산공장 A동')
})

device_update_model = devices_ns.model('DeviceUpdate', {
    'mac_address': fields.String(description='MAC 주소', example='AA:BB:CC:DD:EE:11'),
    'device_name': fields.String(description='기기 이름', example='1공장 정문 카메라'),
    'location': fields.String(description='설치 위치', example='A동 1층')
})

device_response_model = devices_ns.model('DeviceResponse', {
    'device_id': fields.Integer(description='기기 고유 ID'),
    'mac_address': fields.String(description='MAC 주소'),
    'device_name': fields.String(description='기기 이름'),
    'last_known_ip': fields.String(description='마지막 접속 IP'),
    'location': fields.String(description='설치 위치'),
    'is_online': fields.Boolean(description='온라인 여부'),
    'last_connected_at': fields.String(description='마지막 통신 시간'),
    'created_at': fields.String(description='등록일')
})

error_model = devices_ns.model('DeviceErrorResponse', {
    'error': fields.String(description='에러 메시지')
})


# --- [API 리소스 정의] ---

@devices_ns.route('/')
class DeviceList(Resource):

    @devices_ns.doc(
        description='등록된 모든 Jetson 기기 목록을 조회합니다.\n\n'
                    '- 레벨 3(일반 유저): MAC 주소 숨김\n'
                    '- 레벨 2 이하(관리자): 모든 정보 노출',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user):
        """모든 Jetson 기기 목록 조회 (일반 유저는 MAC 주소 숨김)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        devices = JetsonDevice.query.all()
        result = []

        for device in devices:
            device_data = device.to_dict()
            # 레벨 3(일반 유저)이면 MAC 주소를 숨김
            if user_level > 2:
                device_data.pop("mac_address", None)
            result.append(device_data)

        return result, HTTPStatus.OK

    @devices_ns.expect(device_register_model)
    @devices_ns.doc(
        description='새로운 Jetson 기기를 등록합니다. (레벨 2 이상 전용)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def post(self, current_user):
        """새로운 Jetson 기기 등록 (관리자 레벨 2 이상)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        # 레벨 2(관리자) 초과이면 거부 (레벨 3=일반유저)
        if user_level > 2:
            return {"error": "접근 거부: 기기 등록은 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        data = request.get_json()
        mac = data.get('mac_address')
        name = data.get('device_name')

        if not mac or not name:
            return {"error": "MAC 주소와 기기 이름은 필수입니다."}, HTTPStatus.BAD_REQUEST

        if JetsonDevice.query.filter_by(mac_address=mac).first():
            return {"error": "이미 등록된 MAC 주소입니다."}, HTTPStatus.CONFLICT

        new_device = JetsonDevice(
            mac_address=mac,
            device_name=name,
            location=data.get('location'),
            owner_id=current_user.id
        )

        db.session.add(new_device)
        db.session.commit()

        return {"message": "새 기기가 성공적으로 등록되었습니다.", "device": new_device.to_dict()}, HTTPStatus.CREATED


@devices_ns.route('/<int:device_id>')
@devices_ns.param('device_id', '조회/수정/삭제할 기기의 고유 ID 번호')
class DeviceDetail(Resource):

    @devices_ns.doc(
        description='특정 Jetson 기기의 상세 정보를 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user, device_id):
        """특정 Jetson 기기 상세 조회"""
        user_level = current_user.role_info.level if current_user.role_info else 3
        device = JetsonDevice.query.get_or_404(device_id)

        device_data = device.to_dict()
        if user_level > 2:
            device_data.pop("mac_address", None)

        return device_data, HTTPStatus.OK

    @devices_ns.expect(device_update_model)
    @devices_ns.doc(
        description='Jetson 기기 정보를 수정합니다. (레벨 2 이상 전용)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def put(self, current_user, device_id):
        """Jetson 기기 정보 수정 (관리자 레벨 2 이상)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        if user_level > 2:
            return {"error": "접근 거부: 기기 수정은 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        device = JetsonDevice.query.get_or_404(device_id)
        data = request.get_json()

        if 'mac_address' in data:
            # 다른 기기와 MAC 주소 중복 체크
            existing = JetsonDevice.query.filter_by(mac_address=data['mac_address']).first()
            if existing and existing.device_id != device.device_id:
                return {"error": "이미 다른 기기에 등록된 MAC 주소입니다."}, HTTPStatus.CONFLICT
            device.mac_address = data['mac_address']
        if 'device_name' in data:
            device.device_name = data['device_name']
        if 'location' in data:
            device.location = data['location']

        db.session.commit()
        return {"message": "기기 정보가 수정되었습니다.", "device": device.to_dict()}, HTTPStatus.OK

    @devices_ns.doc(
        description='Jetson 기기를 시스템에서 삭제합니다. (관리자 레벨 2 이상)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def delete(self, current_user, device_id):
        """Jetson 기기 삭제 (관리자 레벨 2 이상)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        if user_level > 2:
            return {"error": "접근 거부: 기기 삭제는 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        device = JetsonDevice.query.get_or_404(device_id)
        db.session.delete(device)
        db.session.commit()
        return {"message": f"기기({device.device_name})가 완전히 삭제되었습니다."}, HTTPStatus.OK
