import socket
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8080
INDEX_FILE = Path(__file__).with_name("index.html")


def build_response() -> bytes:
    body = INDEX_FILE.read_bytes()
    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=UTF-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    return headers.encode("utf-8") + body


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"HTTP-сервер запущен: http://{HOST}:{PORT}/")

        while True:
            conn, address = server_socket.accept()
            with conn:
                request = conn.recv(4096).decode("utf-8", errors="replace")
                first_line = request.split("\r\n", 1)[0]
                print(f"[сервер] {address}: {first_line}")
                conn.sendall(build_response())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")