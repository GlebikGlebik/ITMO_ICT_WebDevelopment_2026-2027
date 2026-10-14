import socket

HOST = "127.0.0.1"
PORT = 9002
PARAMS = []

from trapezoid import *

def calculate(line: str) -> str:
    """Разбирает строку с параметрами и вызывает функцию варианта."""
    coef = list(map(str,line.split()))
    if len(coef) != 3:
        return f"""
        ОШИБКА: ожидается параметров: 3, получено: {len(coef)}. Введите параметры в формате: x x x через пробел
        """
    try:
        numbers = [float(p.replace(",", ".")) for p in coef]
    except ValueError:
        return "ОШИБКА: параметры должны быть числами"
    try:
        return "OK: " + trapezoid(numbers[0], numbers[1], numbers[2])
    except ValueError as exc:  # недопустимые значения (например, отрицательная длина)
        return f"ОШИБКА: {exc}"


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"TCP-сервер запущен на {HOST}:{PORT}. Операция: Поиск площади трапеции")

        while True:
            conn, address = server_socket.accept()
            with conn:
                print(f"[сервер] подключение от {address}")
                with conn.makefile("r", encoding="utf-8", newline="\n") as reader:
                    line = reader.readline().strip()
                print(f"[сервер] получено: {line!r}")
                answer = calculate(line)
                print(f"[сервер] отправляю: {answer}")
                conn.sendall((answer + "\n").encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")