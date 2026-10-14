import socket

HOST = "127.0.0.1"
PORT = 9001
BUFFER_SIZE = 1024

def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((HOST, PORT))
        print(f"UDP-сервер запущен на {HOST}:{PORT}. Ожидание сообщения...")
        while True:
            data, client_address = server_socket.recvfrom(BUFFER_SIZE)
            print(f"[сервер] от {client_address}: {data.decode('utf-8')}")
            server_socket.sendto("Hello, client".encode("utf-8"), client_address)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")