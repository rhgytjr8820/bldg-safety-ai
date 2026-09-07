from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
import redis

bcrypt = Bcrypt()
db = SQLAlchemy()
api = Api(
    title='Swagger API',
    version='1.0',
    description='Swagger API 문서',
    doc='/swagger'
)

# Redis 클라이언트 (토큰 블랙리스트 & 세션 관리)
# create_app()에서 Config 값으로 재설정됨
redis_client = None
