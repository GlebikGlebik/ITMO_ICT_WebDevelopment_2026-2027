import socket

SERVER_ADDRESS = ("127.0.0.1", 9002)

from trapezoid import *

def main() -> None:
    print(f"Операция: Поиск площади трапеции")
    values = [input(f"Введите {name}: ").strip() for name in PARAMS]

    try:
        with socket.create_connection(SERVER_ADDRESS, timeout=5) as client_socket:
            client_socket.sendall((" ".join(values) + "\n").encode("utf-8"))
            with client_socket.makefile("r", encoding="utf-8", newline="\n") as reader:
                answer = reader.readline().strip()
    except OSError as exc:
        print(f"Не удалось связаться с сервером: {exc}")
        return

    print(f"Ответ сервера: {answer}")


if __name__ == "__main__":
    main()