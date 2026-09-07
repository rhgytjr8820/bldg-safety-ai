from app.extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Role 테이블과 연결 (3단계 권한 시스템)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)

    # 내가 담당하는 Jetson 기기 목록과의 연결
    devices = db.relationship('JetsonDevice', backref='owner', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role_name": self.role_info.role_name if self.role_info else None,
            "level": self.role_info.level if self.role_info else 3,
            "created_at": self.created_at.isoformat()
        }
