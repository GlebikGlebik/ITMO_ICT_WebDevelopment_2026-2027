import html
import socket
import threading
from urllib.parse import parse_qs

HOST = "127.0.0.1"
PORT = 8080
MAX_HEADERS = 16 * 1024
MAX_BODY = 64 * 1024
MIN_GRADE, MAX_GRADE = 1, 5

grades: dict[str, list[int]] = {}
grades_lock = threading.Lock()


class BadRequest(Exception):
    pass


def read_request(conn: socket.socket) -> tuple[str, str, dict[str, str], bytes]:
    """Возвращает (метод, путь, заголовки, тело). Читает ровно Content-Length байт тела."""
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            raise BadRequest("соединение закрыто до конца заголовков")
        data += chunk
        if len(data) > MAX_HEADERS:
            raise BadRequest("слишком большие заголовки")

    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("utf-8", errors="replace").split("\r\n")
    try:
        method, path, _version = lines[0].split(" ", 2)
    except ValueError:
        raise BadRequest("некорректная стартовая строка")

    headers = {}
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if sep:
            headers[name.strip().lower()] = value.strip()

    try:
        length = int(headers.get("content-length", "0"))
    except ValueError:
        raise BadRequest("некорректный Content-Length")
    if length < 0 or length > MAX_BODY:
        raise BadRequest("недопустимая длина тела")
    while len(body) < length:
        chunk = conn.recv(4096)
        if not chunk:
            break
        body += chunk
    return method, path.split("?", 1)[0], headers, body[:length]


# ---------- формирование ответа ----------
def make_response(status: str, body: str = "", extra_headers: dict | None = None) -> bytes:
    payload = body.encode("utf-8")
    headers = {
        "Content-Type": "text/html; charset=UTF-8",
        "Content-Length": str(len(payload)),
        "Connection": "close",
        **(extra_headers or {}),
    }
    head = f"HTTP/1.1 {status}\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"
    return head.encode("utf-8") + payload


def render_page(message: str = "") -> str:
    with grades_lock:
        snapshot = {subject: list(marks) for subject, marks in grades.items()}

    if snapshot:
        rows = "".join(
            f"<tr><td>{html.escape(subject)}</td>"
            f"<td>{', '.join(map(str, marks))}</td>"
            f"<td>{sum(marks) / len(marks):.2f}</td></tr>"
            for subject, marks in sorted(snapshot.items())
        )
        table = ("<table><tr><th>Дисциплина</th><th>Оценки</th><th>Средний балл</th></tr>"
                 + rows + "</table>")
    else:
        table = "<p>Оценок пока нет.</p>"

    note = f'<p class="err">{html.escape(message)}</p>' if message else ""
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><title>Журнал оценок</title>
<style>
 body {{ font-family: sans-serif; max-width: 640px; margin: 2rem auto; }}
 table {{ border-collapse: collapse; width: 100%; }}
 td, th {{ border: 1px solid #999; padding: .4rem .6rem; text-align: left; }}
 .err {{ color: #b00020; }}
</style></head><body>
<h1>Журнал оценок</h1>
{note}
{table}
<h2>Добавить оценку</h2>
<form method="POST" action="/grades">
  <input name="subject" placeholder="Дисциплина" required>
  <input name="grade" type="number" min="{MIN_GRADE}" max="{MAX_GRADE}" placeholder="Оценка" required>
  <button type="submit">Сохранить</button>
</form></body></html>"""


# ---------- обработчики ----------
def handle_get(path: str) -> bytes:
    if path == "/":
        return make_response("200 OK", render_page())
    return make_response("404 Not Found", "<h1>404 — страница не найдена</h1>")


def handle_post(path: str, body: bytes) -> bytes:
    if path != "/grades":
        return make_response("404 Not Found", "<h1>404 — страница не найдена</h1>")

    form = parse_qs(body.decode("utf-8", errors="replace"))
    subject = form.get("subject", [""])[0].strip()
    raw_grade = form.get("grade", [""])[0].strip()

    if not subject:
        return make_response("400 Bad Request", render_page("Не указана дисциплина"))
    try:
        grade = int(raw_grade)
    except ValueError:
        return make_response("400 Bad Request", render_page("Оценка должна быть целым числом"))
    if not MIN_GRADE <= grade <= MAX_GRADE:
        return make_response(
            "400 Bad Request", render_page(f"Оценка должна быть от {MIN_GRADE} до {MAX_GRADE}"))

    with grades_lock:
        grades.setdefault(subject, []).append(grade)  # группировка по предмету
    # Post/Redirect/Get: после обновления страницы форма не отправится повторно
    return make_response("303 See Other", "", {"Location": "/"})


def handle_client(conn: socket.socket, address) -> None:
    with conn:
        try:
            conn.settimeout(10)
            method, path, _headers, body = read_request(conn)
            print(f"[сервер] {address[0]}:{address[1]} {method} {path}")
            if method == "GET":
                response = handle_get(path)
            elif method == "POST":
                response = handle_post(path, body)
            else:
                response = make_response("405 Method Not Allowed", "<h1>405</h1>",
                                         {"Allow": "GET, POST"})
        except BadRequest as exc:
            response = make_response("400 Bad Request", f"<h1>400 — {html.escape(str(exc))}</h1>")
        except OSError:
            return  # клиент отвалился или таймаут
        try:
            conn.sendall(response)
        except OSError:
            pass


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(16)
        print(f"Сервер журнала запущен: http://{HOST}:{PORT}/")

        while True:
            conn, address = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, address), daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")