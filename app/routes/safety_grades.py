from flask_restx import Namespace, Resource, fields
from app.models.safety_grade import SafetyGrade
from app.extensions import db

grade_ns = Namespace('safety-grades', description='시설물 안전등급 기준 API')

# Swagger에 보여질 응답 데이터 구조 (DTO)
grade_model = grade_ns.model('SafetyGrade', {
    'grade': fields.String(description='안전 등급 (A~E)', example='A'),
    'label': fields.String(description='등급명', example='우수'),
    'state': fields.String(description='상태 요약', example='문제없음'),
    'description': fields.String(description='상세 기준 요약')
})

@grade_ns.route('/')
class SafetyGradeList(Resource):
    @grade_ns.marshal_list_with(grade_model)
    def get(self):
        """시설물 안전등급 기준표 전체 조회"""
        # A부터 E까지 정렬해서 반환
        return SafetyGrade.query.order_by(SafetyGrade.grade).all()
