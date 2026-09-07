from app.extensions import db

class SafetyGrade(db.Model):
    __tablename__ = 'safety_grades'

    # A, B, C, D, E 가 그대로 PK가 됩니다.
    grade = db.Column(db.String(2), primary_key=True)
    label = db.Column(db.String(10), nullable=False)       # 예: 우수, 양호, 보통
    state = db.Column(db.String(50), nullable=False)       # 예: 문제없음, 경미한 결함
    description = db.Column(db.Text, nullable=False)       # 기준 요약 설명

    def to_dict(self):
        return {
            "grade": self.grade,
            "label": self.label,
            "state": self.state,
            "description": self.description
        }
