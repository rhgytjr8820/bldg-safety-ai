from datetime import datetime
from app.extensions import db

# ==========================================
# 2. 위험도 평가 테이블 (비즈니스 로직) - Defect를 부모로 참조
# ==========================================
class RiskAssessment(db.Model):
    __tablename__ = 'risk_assessments'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    # 부모를 detections.id 에서 defects.defect_id 로 변경
    defect_id = db.Column(db.Integer, db.ForeignKey('defects.defect_id'), nullable=False)
    assessed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    risk_score = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(20), index=True, nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    is_complex = db.Column(db.Boolean, default=False, nullable=False)  # 복합 결함 여부

    # 1:N 관계 (하나의 위험도 평가로 인해 슬랙, 대시보드 등 여러 알림이 발생할 수 있음)
    alerts = db.relationship('Alert', backref='risk_assessment', lazy=True, cascade="all, delete-orphan")


# ==========================================
# 3. 알림 이력 테이블 (액션 및 조치)
# ==========================================
class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    risk_id = db.Column(db.BigInteger, db.ForeignKey('risk_assessments.id'), nullable=False)

    channel = db.Column(db.String(50), nullable=False)  # 예: 'mqtt', 'slack', 'dashboard'
    status = db.Column(db.String(20), default='SENT', nullable=False)  # 'SENT', 'FAIL', 'ACK'

    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ack_at = db.Column(db.DateTime, nullable=True)  # 관리자 확인 시각
