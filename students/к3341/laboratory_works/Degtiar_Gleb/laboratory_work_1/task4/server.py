import socket
import threading

HOST = "127.0.0.1"
PORT = 9004
MAX_NAME_LEN = 20

clients: dict[str, socket.socket] = {}  # имя -> сокет
clients_lock = threading.Lock()         # словарь меняют сразу несколько потоков


def send_line(conn: socket.socket, text: str) -> bool:
    try:
        conn.sendall((text + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def broadcast(text: str, exclude: str | None = None) -> None:
    """Рассылает сообщение всем, кроме exclude (отправителя)."""
    with clients_lock:
        recipients = [(n, c) for n, c in clients.items() if n != exclude]
    for _, conn in recipients:
        send_line(conn, text)


def register(conn: socket.socket, reader) -> str | None:
    """Читает имя, проверяет его и регистрирует клиента. None — отказ."""
    name = reader.readline().strip()
    if not name or len(name) > MAX_NAME_LEN or " " in name:
        send_line(conn, f"ERR имя должно быть без пробелов, 1-{MAX_NAME_LEN} символов")
        return None
    with clients_lock:
        if name in clients:
            send_line(conn, "ERR имя уже занято")
            return None
        clients[name] = conn
    send_line(conn, "OK")
    return name


def handle_client(conn: socket.socket, address) -> None:
    """Выполняется в отдельном потоке для каждого клиента."""
    name = None
    try:
        with conn.makefile("r", encoding="utf-8", newline="\n") as reader:
            name = register(conn, reader)
            if name is None:
                return
            print(f"[сервер] {name} подключился ({address})")
            broadcast(f"*** {name} вошёл в чат ***", exclude=name)
            send_line(conn, f"Добро пожаловать, {name}! Выход: /quit")

            for line in reader:
                text = line.strip()
                if text == "/quit":
                    break
                if text:
                    broadcast(f"[{name}] {text}", exclude=name)
    except (OSError, UnicodeDecodeError):
        pass  # обрыв соединения — обрабатываем как выход
    finally:
        if name is not None:
            with clients_lock:
                clients.pop(name, None)
            broadcast(f"*** {name} покинул чат ***")
            print(f"[сервер] {name} отключился")
        conn.close()


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"Чат-сервер запущен на {HOST}:{PORT}")

        while True:
            conn, address = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, address), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")