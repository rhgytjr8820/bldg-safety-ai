from flask import request
from flask_restx import Namespace, Resource, fields
from datetime import datetime
from app.extensions import db
from app.services.auth_service import token_required
from http import HTTPStatus

# 핵심 수정: Building과 Defect 모델을 합쳐진 하나의 파일에서 동시에 가져옵니다!
from app.models.building import Building, Defect

# ==========================================
# 1. Namespace 및 Swagger Model (DTO) 정의
# ==========================================
building_ns = Namespace('buildings', description='건물 정보 관리 API')
defect_ns = Namespace('defects', description='결함 탐지 이력 관리 API')

building_model = building_ns.model('Building', {
    'building_name': fields.String(required=True, description='건물 이름'),
    'location': fields.String(required=True, description='건물 위치'),
    'completion_date': fields.String(description='완공일자 (YYYY-MM-DD)')
})

defect_model = defect_ns.model('Defect', {
    'building_id': fields.Integer(required=True, description='건물 ID'),
    'device_id': fields.Integer(required=True, description='탐지 기기(Jetson) ID'),
    'defect_type': fields.String(required=True, description='결함 유형 (예: 화재, 균열)'),
    'severity': fields.String(description='심각도 (경미/주의/심각)', example='주의'),
    'image_url': fields.String(description='AI 촬영 결함 사진 경로', example='/uploads/defects/fire_01.jpg'),
    'comment': fields.String(description='상세 설명'),
    'confidence': fields.Float(description='AI 확신도 (0.0 ~ 1.0)', example=0.95),
    'bbox': fields.String(description='결함 바운딩 박스 위치 좌표', example='[100, 200, 150, 250]'),
    'size_px': fields.Float(description='결함 크기/면적', example=45.2)
})

# ==========================================
# 🏢 2. 건물(Building) 관련 API 라우트
# ==========================================
@building_ns.route('/')
class BuildingList(Resource):
    @building_ns.doc(
        description='등록된 모든 건물 목록을 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user):
        """등록된 모든 건물 목록 조회"""
        buildings = Building.query.all()
        return [b.to_dict() for b in buildings], HTTPStatus.OK

    @building_ns.expect(building_model)
    @building_ns.doc(
        description='새로운 건물 정보를 등록합니다. (관리자 레벨 2 이상)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def post(self, current_user):
        """새로운 건물 정보 등록 (관리자 레벨 2 이상)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        if user_level > 2:
            return {"error": "접근 거부: 건물 등록은 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        data = request.get_json()
        if not data:
            return {"error": "요청 본문(body)이 비어있습니다."}, HTTPStatus.BAD_REQUEST

        try:
            comp_date = datetime.strptime(data['completion_date'], '%Y-%m-%d').date() if data.get('completion_date') else None
            new_building = Building(
                building_name=data['building_name'],
                location=data['location'],
                completion_date=comp_date
            )
            db.session.add(new_building)
            db.session.commit()
            return {'message': '건물이 성공적으로 등록되었습니다.', 'building': new_building.to_dict()}, HTTPStatus.CREATED
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.BAD_REQUEST


@building_ns.route('/<int:building_id>')
@building_ns.param('building_id', '조회/삭제할 건물의 고유 ID')
class BuildingDetail(Resource):
    @building_ns.doc(
        description='특정 건물의 상세 정보를 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user, building_id):
        """특정 건물 상세 조회"""
        building = Building.query.get_or_404(building_id)
        return building.to_dict(), HTTPStatus.OK

    @building_ns.expect(building_model)
    @building_ns.doc(
        description='건물 정보를 수정합니다. (관리자 레벨 2 이상)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def put(self, current_user, building_id):
        """건물 정보 수정 (관리자 레벨 2 이상)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        if user_level > 2:
            return {"error": "접근 거부: 건물 수정은 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        building = Building.query.get_or_404(building_id)
        data = request.get_json()

        if 'building_name' in data:
            building.building_name = data['building_name']
        if 'location' in data:
            building.location = data['location']
        if 'completion_date' in data:
            try:
                building.completion_date = datetime.strptime(data['completion_date'], '%Y-%m-%d').date() if data['completion_date'] else None
            except ValueError:
                return {"error": "완공일자 형식이 올바르지 않습니다. (YYYY-MM-DD)"}, HTTPStatus.BAD_REQUEST

        db.session.commit()
        return {"message": "건물 정보가 수정되었습니다.", "building": building.to_dict()}, HTTPStatus.OK

    @building_ns.doc(
        description='건물 정보를 삭제합니다. (관리자 레벨 2 이상)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def delete(self, current_user, building_id):
        """건물 삭제 (관리자 레벨 2 이상)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        if user_level > 2:
            return {"error": "접근 거부: 건물 삭제는 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        building = Building.query.get_or_404(building_id)

        # 해당 건물에 연결된 결함 이력이 있으면 삭제 거부
        if building.defects:
            return {"error": f"이 건물에 {len(building.defects)}건의 결함 이력이 남아있어 삭제할 수 없습니다. 결함 이력을 먼저 삭제해주세요."}, HTTPStatus.CONFLICT

        db.session.delete(building)
        db.session.commit()
        return {"message": f"건물({building.building_name})이 삭제되었습니다."}, HTTPStatus.OK


# ==========================================
#  3. 결함(Defect) 관련 API 라우트
# ==========================================
@defect_ns.route('/')
class DefectList(Resource):
    @defect_ns.doc(
        description='전체 결함 탐지 이력을 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user):
        """전체 결함 탐지 이력 조회"""
        defects = Defect.query.all()
        return [d.to_dict() for d in defects], HTTPStatus.OK

    @defect_ns.expect(defect_model)
    @defect_ns.doc(
        description='결함 정보를 등록합니다. (모든 인증된 사용자 가능)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def post(self, current_user):
        """결함 정보 등록 (모든 인증된 사용자 가능)"""
        data = request.get_json()
        if not data:
            return {"error": "요청 본문(body)이 비어있습니다."}, HTTPStatus.BAD_REQUEST

        try:
            new_defect = Defect(
                building_id=data['building_id'],
                device_id=data['device_id'],
                defect_type=data['defect_type'],
                severity=data.get('severity'),
                image_url=data.get('image_url'),
                comment=data.get('comment'),
                confidence=data.get('confidence'),
                bbox=data.get('bbox'),
                size_px=data.get('size_px')
            )
            db.session.add(new_defect)
            db.session.commit()
            return {'message': '결함 이력이 저장되었습니다.', 'defect': new_defect.to_dict()}, HTTPStatus.CREATED
        except Exception as e:
            return {'error': str(e)}, HTTPStatus.BAD_REQUEST


@defect_ns.route('/<int:defect_id>')
@defect_ns.param('defect_id', '조회/수정/삭제할 결함의 고유 ID')
class DefectDetail(Resource):
    @defect_ns.doc(
        description='특정 결함의 상세 정보를 조회합니다.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def get(self, current_user, defect_id):
        """특정 결함 상세 조회"""
        defect = Defect.query.get_or_404(defect_id)
        return defect.to_dict(), HTTPStatus.OK

    @defect_ns.expect(defect_model)
    @defect_ns.doc(
        description='결함 정보를 수정합니다. (메모, 심각도, 결함유형, 이미지 등)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def put(self, current_user, defect_id):
        """결함 정보 수정 (모든 인증된 사용자 가능)"""
        defect = Defect.query.get_or_404(defect_id)
        data = request.get_json()

        if 'comment' in data:
            defect.comment = data['comment']
        if 'severity' in data:
            defect.severity = data['severity']
        if 'defect_type' in data:
            defect.defect_type = data['defect_type']
        if 'image_url' in data:
            defect.image_url = data['image_url']
        if 'confidence' in data:
            defect.confidence = data['confidence']
        if 'bbox' in data:
            defect.bbox = data['bbox']
        if 'size_px' in data:
            defect.size_px = data['size_px']

        db.session.commit()
        return {"message": "결함 정보가 수정되었습니다.", "defect": defect.to_dict()}, HTTPStatus.OK

    @defect_ns.expect(defect_model)
    @defect_ns.doc(
        description='결함 정보를 부분 수정합니다. (PATCH - 프론트엔드 호환용, PUT과 동일 동작)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def patch(self, current_user, defect_id):
        """결함 정보 부분 수정 (PATCH)"""
        defect = Defect.query.get_or_404(defect_id)
        data = request.get_json()

        if 'comment' in data:
            defect.comment = data['comment']
        if 'severity' in data:
            defect.severity = data['severity']
        if 'defect_type' in data:
            defect.defect_type = data['defect_type']
        if 'image_url' in data:
            defect.image_url = data['image_url']
        if 'confidence' in data:
            defect.confidence = data['confidence']
        if 'bbox' in data:
            defect.bbox = data['bbox']
        if 'size_px' in data:
            defect.size_px = data['size_px']

        db.session.commit()
        return {"message": "결함 정보가 수정되었습니다.", "defect": defect.to_dict()}, HTTPStatus.OK

    @defect_ns.doc(
        description='결함 이력을 삭제합니다. (관리자 레벨 2 이상)',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def delete(self, current_user, defect_id):
        """결함 삭제 (관리자 레벨 2 이상)"""
        user_level = current_user.role_info.level if current_user.role_info else 3

        if user_level > 2:
            return {"error": "접근 거부: 결함 삭제는 관리자(레벨 2) 이상만 가능합니다."}, HTTPStatus.FORBIDDEN

        defect = Defect.query.get_or_404(defect_id)
        db.session.delete(defect)
        db.session.commit()
        return {"message": f"결함(ID: {defect_id})이 삭제되었습니다."}, HTTPStatus.OK
