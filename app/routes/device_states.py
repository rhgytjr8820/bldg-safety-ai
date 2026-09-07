from flask import request
from flask_restx import Namespace, Resource, fields
from app.models.device_state import DeviceState
from app.models.device import JetsonDevice
from app.services.auth_service import token_required
from app.extensions import db
from http import HTTPStatus

# 네임스페이스 생성
device_state_ns = Namespace('device-states', description='장비 실시간 상태 모니터링 API')

# --- [Swagger 데이터 모델 정의] ---
state_model = device_state_ns.model('DeviceState', {
    'id': fields.Integer(description='상태 기록 ID'),
    'device_id': fields.Integer(description='장비 ID'),
    'recorded_at': fields.String(description='기록 시각'),
    'cpu_usage': fields.Float(description='CPU 사용률 (%)'),
    'gpu_usage': fields.Float(description='GPU 사용률 (%)'),
    'gpu_memory_usage': fields.Float(description='GPU 메모리 사용률 (%)'),
    'ram_usage': fields.Float(description='RAM 사용률 (%)'),
    'temperature_soc': fields.Float(description='SoC 온도 (℃)'),
    'temperature_cpu': fields.Float(description='CPU 온도 (℃)'),
    'temperature_gpu': fields.Float(description='GPU 온도 (℃)'),
    'inference_fps': fields.Float(description='추론 FPS'),
    'model_name': fields.String(description='실행 중인 AI 모델명'),
    'camera_status': fields.String(description='카메라 상태'),
    'depth_sensor_status': fields.String(description='깊이 센서 상태')
})

state_input_model = device_state_ns.model('DeviceStateInput', {
    'device_id': fields.Integer(required=True, description='장비 ID', example=35),
    'cpu_usage': fields.Float(description='CPU 사용률 (%)', example=45.2),
    'gpu_usage': fields.Float(description='GPU 사용률 (%)', example=78.5),
    'gpu_memory_usage': fields.Float(description='GPU 메모리 사용률 (%)', example=60.0),
    'ram_usage': fields.Float(description='RAM 사용률 (%)', example=52.3),
    'temperature_soc': fields.Float(description='SoC 온도 (℃)', example=42.0),
    'temperature_cpu': fields.Float(description='CPU 온도 (℃)', example=55.0),
    'temperature_gpu': fields.Float(description='GPU 온도 (℃)', example=63.0),
    'inference_fps': fields.Float(description='추론 FPS', example=30.0),
    'model_name': fields.String(description='AI 모델명', example='yolov8n_engine'),
    'camera_status': fields.String(description='카메라 상태', example='OK'),
    'depth_sensor_status': fields.String(description='깊이 센서 상태', example='OK')
})


# --- [API 리소스 정의] ---

@device_state_ns.route('/<int:device_id>')
@device_state_ns.param('device_id', '조회할 장비의 고유 ID')
class DeviceStateLatest(Resource):

    @device_state_ns.doc(
        description='특정 장비의 최신 상태를 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user, device_id):
        """특정 장비의 최신 상태 조회"""
        device = JetsonDevice.query.get_or_404(device_id)
        latest = DeviceState.query.filter_by(device_id=device_id)\
            .order_by(DeviceState.recorded_at.desc()).first()

        if not latest:
            return {"message": f"장비(ID: {device_id})의 상태 기록이 아직 없습니다."}, HTTPStatus.NOT_FOUND

        return latest.to_dict(), HTTPStatus.OK


@device_state_ns.route('/<int:device_id>/history')
@device_state_ns.param('device_id', '조회할 장비의 고유 ID')
class DeviceStateHistory(Resource):

    @device_state_ns.doc(
        description='특정 장비의 상태 이력을 최근 50건까지 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user, device_id):
        """특정 장비 상태 이력 조회 (최근 50건)"""
        device = JetsonDevice.query.get_or_404(device_id)
        states = DeviceState.query.filter_by(device_id=device_id)\
            .order_by(DeviceState.recorded_at.desc()).limit(50).all()

        return [s.to_dict() for s in states], HTTPStatus.OK


@device_state_ns.route('/')
class DeviceStateAll(Resource):

    @device_state_ns.doc(
        description='모든 온라인 장비의 최신 상태를 한 번에 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user):
        """전체 장비 최신 상태 일괄 조회"""
        devices = JetsonDevice.query.all()
        result = []

        for device in devices:
            latest = DeviceState.query.filter_by(device_id=device.device_id)\
                .order_by(DeviceState.recorded_at.desc()).first()
            if latest:
                state_data = latest.to_dict()
                state_data['device_name'] = device.device_name
                state_data['is_online'] = device.is_online
                result.append(state_data)

        return result, HTTPStatus.OK

    @device_state_ns.expect(state_input_model)
    @device_state_ns.doc(
        description='장비 상태를 등록합니다. (모든 인증된 사용자 가능)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def post(self, current_user):
        """장비 상태 등록"""
        data = request.get_json()
        if not data:
            return {"error": "요청 본문(body)이 비어있습니다."}, HTTPStatus.BAD_REQUEST

        device_id = data.get('device_id')
        if not device_id:
            return {"error": "device_id는 필수입니다."}, HTTPStatus.BAD_REQUEST

        device = JetsonDevice.query.get(device_id)
        if not device:
            return {"error": f"장비(ID: {device_id})를 찾을 수 없습니다."}, HTTPStatus.NOT_FOUND

        new_state = DeviceState(
            device_id=device_id,
            cpu_usage=data.get('cpu_usage', 0.0),
            gpu_usage=data.get('gpu_usage', 0.0),
            gpu_memory_usage=data.get('gpu_memory_usage', 0.0),
            ram_usage=data.get('ram_usage', 0.0),
            temperature_soc=data.get('temperature_soc', 0.0),
            temperature_cpu=data.get('temperature_cpu', 0.0),
            temperature_gpu=data.get('temperature_gpu', 0.0),
            inference_fps=data.get('inference_fps'),
            model_name=data.get('model_name'),
            camera_status=data.get('camera_status'),
            depth_sensor_status=data.get('depth_sensor_status')
        )
        db.session.add(new_state)
        db.session.commit()

        return {"message": "장비 상태가 저장되었습니다.", "state": new_state.to_dict()}, HTTPStatus.CREATED

