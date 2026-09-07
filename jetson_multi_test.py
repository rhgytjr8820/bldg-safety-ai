import socket
import json
import time
import random
import threading


# 1대의 기기가 독립적으로 움직이는 함수
def start_device(device_id, mac_address):
    server_ip = '127.0.0.1'
    server_port = 5001

    print(f"🚀 [공장 {device_id}동 기기] 부팅 완료! (MAC: {mac_address})")

    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((server_ip, server_port))

            data = json.dumps({"mac_address": mac_address, "status": "alive"})
            client.send(data.encode('utf-8'))

            response = client.recv(1024).decode('utf-8')
            print(f"✅ [기기 {device_id} 응답] {response}")

            client.close()
        except Exception as e:
            print(f"⚠️ [기기 {device_id}] 연결 실패: {e}")

        # 8초~12초 사이 랜덤 간격으로 heartbeat 전송
        time.sleep(random.randint(8, 12))


if __name__ == '__main__':
    # 가짜 기기 5대의 MAC 주소 리스트
    fake_macs = [
        "AA:BB:CC:DD:EE:01",
        "AA:BB:CC:DD:EE:02",
        "AA:BB:CC:DD:EE:03",
        "AA:BB:CC:DD:EE:04",
        "AA:BB:CC:DD:EE:05"
    ]

    print("🌟 대규모 멀티 Jetson 시뮬레이터를 시작합니다...\n")

    # 5대의 기기를 동시에 스레드로 실행
    for i, mac in enumerate(fake_macs, start=1):
        thread = threading.Thread(target=start_device, args=(i, mac))
        thread.daemon = True
        thread.start()
        time.sleep(1)  # 1초 간격으로 순차 부팅

    # 메인 프로그램 유지
    while True:
        time.sleep(100)
