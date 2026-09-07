from datetime import datetime
from app.extensions import db


class DeviceState(db.Model):
    __tablename__ = 'device_states'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.Integer, db.ForeignKey('jetson_devices.device_id'), nullable=False)

    # 기록 시각 (기본값: 현재 UTC 시간)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)

    # ==========================================
    # 💻 연산 자원 (0~100%)
    # ==========================================
    cpu_usage = db.Column(db.Float, nullable=False, default=0.0)
    gpu_usage = db.Column(db.Float, nullable=False, default=0.0)
    gpu_memory_usage = db.Column(db.Float, nullable=False, default=0.0)
    ram_usage = db.Column(db.Float, nullable=False, default=0.0)

    # ==========================================
    # 🔥 온도 (섭씨 ℃)
    # ==========================================
    temperature_soc = db.Column(db.Float, nullable=False, default=0.0)
    temperature_cpu = db.Column(db.Float, nullable=False, default=0.0)
    temperature_gpu = db.Column(db.Float, nullable=False, default=0.0)

    # ==========================================
    # 🚀 추론 및 기기 상태
    # ==========================================
    inference_fps = db.Column(db.Float, nullable=True, default=0.0)
    model_name = db.Column(db.String(100), nullable=True)  # 예: 'yolov8n_engine'
    camera_status = db.Column(db.String(50), nullable=True)  # 예: 'OK', 'ERROR', 'DISCONNECTED'
    depth_sensor_status = db.Column(db.String(50), nullable=True)  # S100D 상태

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "recorded_at": self.recorded_at.isoformat() + 'Z' if self.recorded_at else None,
            "cpu_usage": self.cpu_usage,
            "gpu_usage": self.gpu_usage,
            "gpu_memory_usage": self.gpu_memory_usage,
            "ram_usage": self.ram_usage,
            "temperature_soc": self.temperature_soc,
            "temperature_cpu": self.temperature_cpu,
            "temperature_gpu": self.temperature_gpu,
            "inference_fps": self.inference_fps,
            "model_name": self.model_name,
            "camera_status": self.camera_status,
            "depth_sensor_status": self.depth_sensor_status
        }
