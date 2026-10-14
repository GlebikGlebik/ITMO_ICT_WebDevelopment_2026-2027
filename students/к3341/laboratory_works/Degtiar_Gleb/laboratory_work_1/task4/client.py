import socket
import sys
import threading

SERVER_ADDRESS = ("127.0.0.1", 9004)

disconnected = threading.Event()


def receive_loop(reader) -> None:
    """Отдельный поток: печатает всё, что присылает сервер."""
    try:
        for line in reader:
            print("\r" + line.rstrip("\n"))
    except (OSError, ValueError):
        pass
    finally:
        disconnected.set()
        print("\r[соединение закрыто — нажмите Enter для выхода]")


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else input("Ваше имя: ").strip()

    try:
        sock = socket.create_connection(SERVER_ADDRESS, timeout=5)
    except OSError as exc:
        print(f"Не удалось подключиться к серверу: {exc}")
        return
    sock.settimeout(None)
    reader = sock.makefile("r", encoding="utf-8", newline="\n")

    sock.sendall((name + "\n").encode("utf-8"))
    status = reader.readline().strip()
    if status != "OK":
        print(f"Сервер отклонил имя: {status.removeprefix('ERR ')}")
        sock.close()
        return

    threading.Thread(target=receive_loop, args=(reader,), daemon=True).start()

    try:
        while not disconnected.is_set():
            text = input()
            if disconnected.is_set():
                break
            sock.sendall((text + "\n").encode("utf-8"))
            if text.strip() == "/quit":
                break
    except (EOFError, KeyboardInterrupt):
        try:
            sock.sendall(b"/quit\n")
        except OSError:
            pass
    except OSError:
        pass
    finally:
        sock.close()
        print("Вы вышли из чата.")


if __name__ == "__main__":
    main()