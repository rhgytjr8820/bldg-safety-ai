from datetime import datetime
from app.extensions import db


class Building(db.Model):
    __tablename__ = 'buildings'

    building_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    building_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    completion_date = db.Column(db.Date, nullable=True)         # 완공일자
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 건물과 결함은 1:N 관계
    defects = db.relationship('Defect', backref='building', lazy=True)

    def to_dict(self):
        return {
            "building_id": self.building_id,
            "building_name": self.building_name,
            "location": self.location,
            "completion_date": self.completion_date.strftime("%Y-%m-%d") if self.completion_date else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }

    def __repr__(self):
        return f'<Building {self.building_name}>'


class Defect(db.Model):
    __tablename__ = 'defects'

    defect_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.building_id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('jetson_devices.device_id'), nullable=False)
    defect_type = db.Column(db.String(50), nullable=False)      # 균열(Crack), 화재(Fire) 등
    severity = db.Column(db.String(20), nullable=True)          # 경미 / 주의 / 심각
    image_url = db.Column(db.String(500), nullable=True)        # AI 촬영 결함 사진 경로
    comment = db.Column(db.Text, nullable=True)
    detection_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # --- Detection 테이블 기능 흡수 (AI 상세 분석 데이터) ---
    confidence = db.Column(db.Float, nullable=True)             # 0.0 ~ 1.0 AI 확신도
    bbox = db.Column(db.String(255), nullable=True)             # Bounding Box JSON 문자열
    size_px = db.Column(db.Float, nullable=True)                # 면적 또는 두께
    
    # 1:1 관계 (하나의 결함은 하나의 위험도 평가를 가짐)
    risk_assessment = db.relationship('RiskAssessment', backref='defect', uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "defect_id": self.defect_id,
            "building_id": self.building_id,
            "device_id": self.device_id,
            "defect_type": self.defect_type,
            "severity": self.severity,
            "image_url": self.image_url,
            "comment": self.comment,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "size_px": self.size_px,
            "detection_time": self.detection_time.strftime("%Y-%m-%d %H:%M:%S") if self.detection_time else None
        }

    def __repr__(self):
        return f'<Defect {self.defect_type} at {self.detection_time}>'
