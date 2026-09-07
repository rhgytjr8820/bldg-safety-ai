import socket
import threading
import json
from datetime import datetime
from app.models.device import JetsonDevice
from app.models.device_state import DeviceState
from app.extensions import db


def handle_client(client_socket, addr, app):
    """Jetson 기기 연결을 처리하는 핸들러 함수"""
    print(f"\n🤝 [TCP 서버] 새로운 기기 연결됨: IP={addr[0]}")

    # 백그라운드 스레드에서도 DB를 사용하려면 app_context()가 필요
    with app.app_context():
        mac = None  # finally에서 오프라인 처리를 위해 미리 초기화

        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')

                # 데이터가 비어있으면 기기 쪽에서 연결을 끊은 것
                if not data:
                    print(f"⚠️ [TCP 서버] 기기({addr[0]})가 통신을 종료했습니다.")
                    break

                info = json.loads(data)
                mac = info.get('mac_address')

                if mac:
                    # DB에서 MAC 주소로 기기 찾기
                    device = JetsonDevice.query.filter_by(mac_address=mac).first()

                    if not device:
                        # 미등록 기기는 연결 차단
                        print(f"🚨 보안 경고: 미등록 기기({mac})의 불법 접근 시도! 연결을 차단합니다.")
                        client_socket.send("UNAUTHORIZED: 앱에서 먼저 기기를 등록해주세요.".encode('utf-8'))
                        break

                    # 1. 기기 기본 정보(IP 및 온라인 상태) 업데이트
                    device.last_known_ip = addr[0]
                    device.is_online = True
                    device.last_connected_at = datetime.utcnow()

                    # 2. 메시지 타입(type) 기반 라우팅 (실무 표준 방식)
                    msg_type = info.get('type')
                    
                    # [하위 호환성 유지] 젯슨 파이썬 코드가 아직 업데이트되지 않아 'type' 필드가 없을 경우를 대비한 자동 분류
                    if not msg_type:
                        msg_type = 'telemetry' if ('cpu_usage' in info or 'temperature_cpu' in info) else 'heartbeat'

                    if msg_type == 'heartbeat':
                        print(f"[TCP 서버] 하트비트 수신 (온라인 상태 갱신 완료): MAC={mac}")
                        
                    elif msg_type == 'telemetry':
                        new_state = DeviceState(
                            device_id=device.device_id,
                            cpu_usage=info.get('cpu_usage', 0.0),
                            gpu_usage=info.get('gpu_usage', 0.0),
                            gpu_memory_usage=info.get('gpu_memory_usage', 0.0),
                            ram_usage=info.get('ram_usage', 0.0),
                            temperature_soc=info.get('temperature_soc', 0.0),
                            temperature_cpu=info.get('temperature_cpu', 0.0),
                            temperature_gpu=info.get('temperature_gpu', 0.0),
                            inference_fps=info.get('inference_fps'),
                            model_name=info.get('model_name'),
                            camera_status=info.get('camera_status'),
                            depth_sensor_status=info.get('depth_sensor_status')
                        )
                        db.session.add(new_state)
                        print(f"✅ [TCP 서버] 상태(Telemetry) 기록 완료: MAC={mac}, CPU={info.get('cpu_usage', 0)}%, 온도={info.get('temperature_cpu', 0)}℃")
                    
                    else:
                        print(f"⚠️ [TCP 서버] 알 수 없는 메시지 타입 수신: {msg_type}")

                    # 3. DB 변경사항 커밋 (기기 접속시간 갱신 및 상태 추가 반영)
                    db.session.commit()

                    # Jetson에게 정상 수신 응답 전송
                    client_socket.send('{"status": "ok"}'.encode('utf-8'))

        except ConnectionResetError:
            print(f"⚠️ [TCP 서버] 기기({addr[0]})와의 연결이 비정상적으로 끊어졌습니다.")
        except Exception as e:
            print(f"⚠️ [TCP 서버] 에러 발생: {e}")
        finally:
            # 연결 종료 시 기기 오프라인 처리
            if mac:
                device = JetsonDevice.query.filter_by(mac_address=mac).first()
                if device:
                    device.is_online = False
                    db.session.commit()
                    print(f"📴 [TCP 서버] 기기({mac}) 오프라인 처리 완료")

            client_socket.close()
            print(f"🔌 [TCP 서버] 소켓 통신이 안전하게 닫혔습니다: {addr[0]}")


def start_tcp_server(app, host='0.0.0.0', port=5001):
    """TCP 소켓 서버를 시작하여 Jetson 기기의 heartbeat를 수신"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print(f"[*] TCP 소켓 서버가 {port} 포트에서 기기들을 기다립니다...")

    while True:
        # 기기가 접속할 때마다 새로운 스레드를 배정하여 응대
        client, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(client, addr, app))
        thread.daemon = True  # 메인 서버가 꺼지면 같이 종료
        thread.start()
