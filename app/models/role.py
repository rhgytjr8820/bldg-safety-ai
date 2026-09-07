from app.extensions import db


# 권한(계급) 테이블 — 3단계 레벨 시스템
class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    level = db.Column(db.Integer, nullable=False, default=3)

    # Role ↔ User 관계 설정
    users = db.relationship('User', backref='role_info', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "role_name": self.role_name,
            "description": self.description,
            "level": self.level
        }
