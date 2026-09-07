import socket
import json
import uuid
import time


# 내 컴퓨터의 MAC 주소를 가져오는 함수
def get_mac_address():
    mac_num = hex(uuid.getnode()).replace('0x', '').upper()
    mac = ':'.join(mac_num[i: i + 2] for i in range(0, 12, 2))
    return mac


def start_heartbeat():
    server_ip = '127.0.0.1'   # 백엔드 서버 주소
    server_port = 5001         # TCP 소켓 포트
    my_mac = get_mac_address()

    print(f"가짜 Jetson 부팅 완료. (내 MAC 주소: {my_mac})")
    print("백엔드로 10초마다 생존 신고를 시작합니다...")

    while True:
        try:
            # 1. 백엔드 서버에 소켓 연결
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((server_ip, server_port))

            # 2. MAC 주소를 JSON으로 전송 (mac_address 키 사용!)
            data = json.dumps({"mac_address": my_mac, "status": "alive"})
            client.send(data.encode('utf-8'))

            # 3. 백엔드 응답 수신
            response = client.recv(1024).decode('utf-8')
            print(f"[백엔드 응답] {response}")

            client.close()
        except Exception as e:
            print(f" 백엔드 연결 실패 (서버가 켜져 있나요?): {e}")

        # 10초 간격으로 heartbeat 전송
        time.sleep(10)


if __name__ == '__main__':
    start_heartbeat()
