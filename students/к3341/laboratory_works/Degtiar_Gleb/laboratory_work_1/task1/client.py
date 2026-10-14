import socket

SERVER_ADDRESS = ("127.0.0.1", 9001)
BUFFER_SIZE = 1024
TIMEOUT = 5  # UDP не гарантирует доставку, поэтому ждём ответ ограниченное время


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.settimeout(TIMEOUT)
        client_socket.sendto("Hello, server".encode("utf-8"), SERVER_ADDRESS)

        try:
            data, _ = client_socket.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            print(f"[клиент] Сервер не ответил за {TIMEOUT} с.")
            return
        print(f"[клиент] от сервера: {data.decode('utf-8')}")


if __name__ == "__main__":
    main()