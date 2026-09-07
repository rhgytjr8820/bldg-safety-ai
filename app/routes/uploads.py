import os
import uuid
from datetime import datetime
from http import HTTPStatus
from flask import request, send_from_directory, current_app
from flask_restx import Namespace, Resource
from app.services.auth_service import token_required

upload_ns = Namespace('upload', description='이미지 파일 업로드 API')

# 허용하는 이미지 확장자
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

# 업로드 폴더 경로 (프로젝트 루트/uploads/defects/)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'defects')


def allowed_file(filename):
    """허용된 확장자인지 확인"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_ns.route('/')
class ImageUpload(Resource):
    @upload_ns.doc(
        description='결함 이미지를 서버에 업로드합니다. multipart/form-data로 전송하세요.',
        params={'Authorization': {'in': 'header', 'description': 'Bearer {access_token}', 'required': True}}
    )
    @token_required
    def post(self, current_user):
        """이미지 파일 업로드"""
        if 'file' not in request.files:
            return {"error": "요청에 파일(file)이 포함되어 있지 않습니다."}, HTTPStatus.BAD_REQUEST

        file = request.files['file']

        if file.filename == '':
            return {"error": "파일이 선택되지 않았습니다."}, HTTPStatus.BAD_REQUEST

        if not allowed_file(file.filename):
            return {"error": f"허용되지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}"}, HTTPStatus.BAD_REQUEST

        # 파일명 충돌 방지를 위해 UUID + 타임스탬프로 저장
        ext = file.filename.rsplit('.', 1)[1].lower()
        safe_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"

        # 폴더가 없으면 자동 생성
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
        file.save(filepath)

        # 클라이언트가 접근할 수 있는 URL 경로 반환
        image_url = f"/uploads/defects/{safe_filename}"

        return {
            "message": "이미지가 업로드되었습니다.",
            "image_url": image_url,
            "filename": safe_filename
        }, HTTPStatus.CREATED


@upload_ns.route('/<string:filename>')
@upload_ns.param('filename', '조회할 이미지 파일명')
class ImageServe(Resource):
    @upload_ns.doc(description='업로드된 이미지를 조회합니다. (인증 불필요)')
    def get(self, filename):
        """업로드된 이미지 조회"""
        if not os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
            return {"error": "파일을 찾을 수 없습니다."}, HTTPStatus.NOT_FOUND
        return send_from_directory(UPLOAD_FOLDER, filename)
