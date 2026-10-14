# Отчёт по ЛР1. Работа с сокетами

## Цель работы

Понять принципы межсокетного взаимодействия в вебе и научиться реализовывать базовую
архитектуру «клиент–сервер» на библиотеке `socket` (Python).

## Окружение и структура

- Python 3.12, только стандартная библиотека (`socket`, `threading`, `pathlib`, `html`, `urllib.parse`).
- Для отчёта — `mkdocs` и `mkdocs-material`.

Во всех примерах адрес сервера — `127.0.0.1`, у каждого задания свой порт
(9001, 9002, 8080, 9004, 8080), поэтому серверы заданий 3 и 5 одновременно запускать не нужно.

---

## Задание 1. Обмен сообщениями по UDP

**Условие.** Клиент отправляет серверу «Hello, server», сервер выводит его и отвечает «Hello, client».

**Как устроено.**

- Сокет создаётся с `socket.SOCK_DGRAM` — это UDP. Соединения нет, поэтому у сервера нет `listen()` и `accept()`:
  достаточно `bind()` и пары `recvfrom()` / `sendto()`.
- `recvfrom()` возвращает данные **и адрес отправителя** — именно по нему сервер отвечает.
- UDP не гарантирует доставку, поэтому у клиента стоит таймаут ожидания ответа.

??? info "Код сервера — `task1_udp/server.py`"
    ```python
    """Задание 1. UDP-сервер: принимает «Hello, server», отвечает «Hello, client»."""
    import socket

    HOST = "127.0.0.1"
    PORT = 9001
    BUFFER_SIZE = 1024


    def main() -> None:
        # SOCK_DGRAM — UDP: соединения нет, поэтому нет ни listen(), ни accept()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
            server_socket.bind((HOST, PORT))
            print(f"UDP-сервер запущен на {HOST}:{PORT}. Ожидание сообщения (Ctrl+C — выход)...")

            while True:
                data, client_address = server_socket.recvfrom(BUFFER_SIZE)
                print(f"[сервер] от {client_address}: {data.decode('utf-8')}")
                server_socket.sendto("Hello, client".encode("utf-8"), client_address)


    if __name__ == "__main__":
        try:
            main()
        except KeyboardInterrupt:
            print("\nСервер остановлен.")
    ```

??? info "Код клиента — `task1_udp/client.py`"
    ```python
    """Задание 1. UDP-клиент: отправляет «Hello, server» и печатает ответ сервера."""
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
                print(f"[клиент] Сервер не ответил за {TIMEOUT} с. Он запущен?")
                return
            print(f"[клиент] от сервера: {data.decode('utf-8')}")


    if __name__ == "__main__":
        main()
    ```

**Пример работы.**

=== "Терминал 1: сервер"

    ```text
    UDP-сервер запущен на 127.0.0.1:9001. Ожидание сообщения (Ctrl+C — выход)...
    [сервер] от ('127.0.0.1', 60508): Hello, server
    ```

=== "Терминал 2: клиент"

    ```text
    [клиент] от сервера: Hello, client
    ```

---

## Задание 2. Вычисления через TCP

**Условие.** Клиент запрашивает математическую операцию, параметры вводятся с клавиатуры, сервер
считает и возвращает результат. Вариант: **1 — теорема Пифагора**.

**Протокол прикладного уровня.** TCP — потоковый протокол и сам не разделяет сообщения, поэтому
договариваемся о формате: одно сообщение = одна строка, оканчивающаяся `\n`.

| Направление | Содержимое | Пример |
|-------------|-----------|--------|
| клиент → сервер | числа через пробел | `3 4` |
| сервер → клиент | `OK: <результат>` или `ОШИБКА: <причина>` | `OK: Гипотенуза c = ... = 5.0000` |

**Как устроено.**

- `listen()` + `accept()` на сервере, `connect()` (через `create_connection`) на клиенте.
- Сервер проверяет число параметров, что они числа, и что значения допустимы (катеты > 0);
  при ошибке возвращает понятное сообщение, а не падает.
- Операции вынесены в модуль `operations.py`: в нём реализованы все четыре варианта задания,
  а нужный выбирается константой `VARIANT`. Клиент берёт оттуда названия параметров, сервер — функцию вычисления.

??? info "Код операций — `task2_tcp/operations.py`"
    ```python
    """Математические операции для задания 2.

    Вариант выбирается по порядковому номеру в журнале — измените VARIANT:
        1 — теорема Пифагора
        2 — решение квадратного уравнения
        3 — площадь трапеции
        4 — площадь параллелограмма

    Модуль общий для клиента и сервера: клиент берёт отсюда названия параметров
    (что спросить у пользователя), сервер — функцию вычисления.
    """
    import math

    VARIANT = 1


    def pythagoras(a: float, b: float) -> str:
        if a <= 0 or b <= 0:
            raise ValueError("Катеты должны быть положительными")
        c = math.hypot(a, b)
        return f"Гипотенуза c = sqrt({a:g}^2 + {b:g}^2) = {c:.4f}"


    def quadratic(a: float, b: float, c: float) -> str:
        if a == 0:
            raise ValueError("Коэффициент a не должен быть равен 0")
        d = b * b - 4 * a * c
        if d > 0:
            x1 = (-b + math.sqrt(d)) / (2 * a)
            x2 = (-b - math.sqrt(d)) / (2 * a)
            return f"D = {d:g} > 0, два корня: x1 = {x1:.4f}, x2 = {x2:.4f}"
        if d == 0:
            return f"D = 0, один корень: x = {-b / (2 * a):.4f}"
        return f"D = {d:g} < 0, действительных корней нет"


    def trapezoid(a: float, b: float, h: float) -> str:
        if a <= 0 or b <= 0 or h <= 0:
            raise ValueError("Основания и высота должны быть положительными")
        return f"Площадь трапеции S = (({a:g} + {b:g}) / 2) * {h:g} = {(a + b) / 2 * h:.4f}"


    def parallelogram(a: float, h: float) -> str:
        if a <= 0 or h <= 0:
            raise ValueError("Основание и высота должны быть положительными")
        return f"Площадь параллелограмма S = {a:g} * {h:g} = {a * h:.4f}"


    # номер варианта -> (название, названия параметров, функция)
    OPERATIONS = {
        1: ("Теорема Пифагора", ["катет a", "катет b"], pythagoras),
        2: ("Квадратное уравнение ax^2 + bx + c = 0", ["a", "b", "c"], quadratic),
        3: ("Площадь трапеции", ["основание a", "основание b", "высота h"], trapezoid),
        4: ("Площадь параллелограмма", ["основание a", "высота h"], parallelogram),
    }

    NAME, PARAMS, FUNC = OPERATIONS[VARIANT]
    ```

??? info "Код сервера — `task2_tcp/server.py`"
    ```python
    """Задание 2. TCP-сервер: получает параметры, считает, возвращает результат.

    Протокол: клиент присылает одну строку с числами через пробел, заканчивающуюся
    символом '\n'; сервер отвечает одной строкой текста, тоже заканчивающейся '\n'.
    Ответ начинается с 'OK: ' или 'ОШИБКА: '.
    """
    import socket

    from operations import FUNC, NAME, PARAMS

    HOST = "127.0.0.1"
    PORT = 9002


    def calculate(line: str) -> str:
        """Разбирает строку с параметрами и вызывает функцию варианта."""
        parts = line.split()
        if len(parts) != len(PARAMS):
            return f"ОШИБКА: ожидается параметров: {len(PARAMS)}, получено: {len(parts)}"
        try:
            numbers = [float(p.replace(",", ".")) for p in parts]
        except ValueError:
            return "ОШИБКА: параметры должны быть числами"
        try:
            return "OK: " + FUNC(*numbers)
        except ValueError as exc:  # недопустимые значения (например, отрицательная длина)
            return f"ОШИБКА: {exc}"


    def main() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((HOST, PORT))
            server_socket.listen(5)
            print(f"TCP-сервер запущен на {HOST}:{PORT}. Операция: {NAME}")

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
    ```

??? info "Код клиента — `task2_tcp/client.py`"
    ```python
    """Задание 2. TCP-клиент: вводит параметры с клавиатуры, получает результат."""
    import socket

    from operations import NAME, PARAMS

    SERVER_ADDRESS = ("127.0.0.1", 9002)


    def main() -> None:
        print(f"Операция: {NAME}")
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
    ```

**Пример работы.**

=== "Клиент: корректный ввод"

    ```text
    Операция: Теорема Пифагора
    Введите катет a: 3
    Введите катет b: 4
    Ответ сервера: OK: Гипотенуза c = sqrt(3^2 + 4^2) = 5.0000
    ```

=== "Клиент: отрицательный катет"

    ```text
    Операция: Теорема Пифагора
    Введите катет a: -1
    Введите катет b: 4
    Ответ сервера: ОШИБКА: Катеты должны быть положительными
    ```

=== "Клиент: не число"

    ```text
    Операция: Теорема Пифагора
    Введите катет a: abc
    Введите катет b: 4
    Ответ сервера: ОШИБКА: параметры должны быть числами
    ```

=== "Сервер"

    ```text
    TCP-сервер запущен на 127.0.0.1:9002. Операция: Теорема Пифагора
    [сервер] подключение от ('127.0.0.1', 47362)
    [сервер] получено: '3 4'
    [сервер] отправляю: OK: Гипотенуза c = sqrt(3^2 + 4^2) = 5.0000
    [сервер] подключение от ('127.0.0.1', 47374)
    [сервер] получено: '-1 4'
    [сервер] отправляю: ОШИБКА: Катеты должны быть положительными
    [сервер] подключение от ('127.0.0.1', 47376)
    [сервер] получено: 'abc 4'
    [сервер] отправляю: ОШИБКА: параметры должны быть числами
    ```

---

## Задание 3. Раздача HTML-страницы по HTTP

**Условие.** Клиент подключается к серверу и в ответ получает HTTP-сообщение с HTML-страницей из файла `index.html`.

**Как устроено.**

HTTP-ответ — обычный текст строгого формата: статусная строка, заголовки, пустая строка (`\r\n\r\n`) и тело.

```text
HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Content-Length: <длина тела в байтах>
Connection: close

<содержимое index.html>
```

??? info "Код сервера — `task3_http/server.py`"
    ```python
    """Задание 3. Сервер раздаёт HTML-страницу из index.html по HTTP."""
    import socket
    from pathlib import Path

    HOST = "127.0.0.1"
    PORT = 8080
    INDEX_FILE = Path(__file__).with_name("index.html")  # рядом со скриптом, а не от cwd


    def build_response() -> bytes:
        body = INDEX_FILE.read_bytes()
        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=UTF-8\r\n"
            # Content-Length — длина в БАЙТАХ; len(str) для кириллицы дал бы неверное число
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
    ```

??? info "HTML-страница — `task3_http/index.html`"
    ```html
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Страница с сокет-сервера</title>
    </head>
    <body>
        <h1>Привет! Это страница из файла index.html</h1>
        <p>Её отдаёт сервер, написанный на чистых сокетах Python.</p>
    </body>
    </html>
    ```

**Пример работы.** Запуск `python server.py`, затем в браузере `http://127.0.0.1:8080/` или `curl`:

=== "curl -i"

    ```text
    $ curl -i http://127.0.0.1:8080/
    HTTP/1.1 200 OK
    Content-Type: text/html; charset=UTF-8
    Content-Length: 346
    Connection: close

    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Страница с сокет-сервера</title>
    </head>
    <body>
        <h1>Привет! Это страница из файла index.html</h1>
        <p>Её отдаёт сервер, написанный на чистых сокетах Python.</p>
    </body>
    </html>
    ```

=== "Лог сервера"

    ```text
    HTTP-сервер запущен: http://127.0.0.1:8080/
    [сервер] ('127.0.0.1', 38756): GET / HTTP/1.1
    ```

Заголовок `Content-Length: 346` совпал с реальным размером тела (проверено программно).

---

## Задание 4. Многопользовательский чат (TCP + threading)

**Условие.** Многопользовательский чат с идентификацией пользователей и возможностью выйти.

**Как устроено.**

- **Один** клиентский скрипт `client.py`: имя пользователя передаётся аргументом
  (`python client.py Alice`) или вводится с клавиатуры. Имена в коде не зашиты — каждый участник просто запускает
  свой экземпляр клиента.
- Сервер на каждое подключение запускает отдельный поток (`threading.Thread`), а активные подключения хранит
  в словаре `clients = {имя: сокет}`. Так как словарь меняют сразу несколько потоков, доступ защищён `threading.Lock`.
- На клиенте два потока: главный читает ввод с клавиатуры и отправляет, фоновый печатает всё, что присылает сервер.
- **Идентификация:** первой строкой клиент присылает имя. Сервер отвечает `OK` или `ERR <причина>`
  (имя занято, пустое, содержит пробел, длиннее 20 символов).
- **Выход:** команда `/quit`, а также `Ctrl+C` или обрыв соединения — сервер в любом случае
  убирает пользователя из списка и сообщает остальным.
- Сообщение рассылается всем, кроме отправителя.

| Сообщение | Формат |
|-----------|--------|
| Текст пользователя | `[Alice] Привет всем!` |
| Вход / выход | `*** Bob вошёл в чат ***` / `*** Bob покинул чат ***` |

??? info "Код сервера — `task4_chat/server.py`"
    ```python
    """Задание 4. Многопользовательский TCP-чат.

    Протокол (текстовый, одна команда = одна строка, оканчивающаяся '\n'):
      клиент -> сервер: первая строка — имя пользователя,
                        далее — текст сообщений; '/quit' — выход из чата
      сервер -> клиент: на имя отвечает 'OK' или 'ERR <причина>',
                        затем присылает строки чата
    """
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
    ```

??? info "Код клиента — `task4_chat/client.py`"
    ```python
    """Задание 4. Клиент чата. Один и тот же скрипт запускают все участники.

    Использование:  python client.py [имя]   (если имя не задано — спросим)
    """
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
    ```

**Пример работы.** Сервер и три клиента (Alice, Bob, Carol), запущенные в разных терминалах.
Строки без префикса — то, что пользователь набрал сам.

=== "Alice"

    ```text
    Добро пожаловать, Alice! Выход: /quit

    *** Bob вошёл в чат ***

    *** Carol вошёл в чат ***

    [Bob] Привет, Alice!
    Привет всем!

    *** Bob покинул чат ***

    [Carol] Всем привет, я Carol
    Bob, ты тут?
    /quit
    Вы вышли из чата.
    ```

=== "Bob"

    ```text
    Добро пожаловать, Bob! Выход: /quit

    *** Carol вошёл в чат ***
    Привет, Alice!

    [Alice] Привет всем!
    /quit
    Вы вышли из чата.
    ```

=== "Carol"

    ```text
    Добро пожаловать, Carol! Выход: /quit

    [Bob] Привет, Alice!

    [Alice] Привет всем!

    *** Bob покинул чат ***
    Всем привет, я Carol

    [Alice] Bob, ты тут?

    *** Alice покинул чат ***
    ```

=== "Занятое имя"

    ```text
    Сервер отклонил имя: имя уже занято
    ```

=== "Сервер"

    ```text
    Чат-сервер запущен на 127.0.0.1:9004
    [сервер] Alice подключился (('127.0.0.1', 45724))
    [сервер] Bob подключился (('127.0.0.1', 53392))
    [сервер] Carol подключился (('127.0.0.1', 53406))
    [сервер] Bob отключился
    [сервер] Alice отключился
    [сервер] Carol отключился
    [сервер] Dave подключился (('127.0.0.1', 53408))
    ```

---

## Задание 5. Веб-сервер журнала оценок (GET / POST)

**Условие.** Веб-сервер на `socket`, который принимает информацию о дисциплине и оценке (POST) и
отдаёт все оценки в виде HTML-страницы (GET).

**Маршруты.**

| Метод | Путь | Действие | Ответ |
|-------|------|----------|-------|
| GET | `/` | страница с журналом и формой добавления | `200 OK` |
| POST | `/grades` | тело `subject=<дисциплина>&grade=<оценка>`, сохранить оценку | `303 See Other` → `/` |
| любой другой путь | | | `404 Not Found` |
| другие методы | | | `405 Method Not Allowed` |
| некорректные данные | | пустая дисциплина, оценка не число или вне диапазона 1–5 | `400 Bad Request` |

**Структура хранения.** Журнал группируется по дисциплине, поэтому используется словарь
`dict[str, list[int]]`: ключ — название предмета, значение — список его оценок.
Две оценки по математике дают **одну** запись `"Математика": [5, 4]`, а не две строки.

**Как устроено.**

- Запрос разбирается вручную: читаем из сокета до `\r\n\r\n`, парсим первую строку (`метод путь версия`)
  и заголовки, затем **дочитываем ровно `Content-Length` байт тела** — тело POST может прийти отдельным пакетом
  (проверено отдельным тестом).
- Каждое подключение обрабатывается в отдельном потоке (браузер открывает несколько соединений),
  доступ к словарю защищён `Lock`.
- Пользовательский ввод экранируется через `html.escape`, поэтому введённая разметка не превращается в HTML-теги.
- После успешного POST сервер отвечает `303` с `Location: /` (шаблон Post/Redirect/Get):
  при обновлении страницы браузер не отправит форму повторно.

??? info "Код сервера — `task5_grades/server.py`"
    ```python
    """Задание 5. Веб-сервер журнала оценок на чистых сокетах (GET и POST).

      GET  /        -> HTML-страница: журнал, сгруппированный по дисциплинам + форма
      POST /grades  -> принимает subject=<дисциплина>&grade=<оценка>
                       (application/x-www-form-urlencoded), сохраняет, 303 -> /

    Хранилище: dict {дисциплина: [оценки]} — одна запись на предмет, оценки списком.
    """
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


    # ---------- разбор запроса ----------
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
    ```

**Пример работы.** Запуск `python server.py`, затем `curl` (или форма в браузере на `http://127.0.0.1:8080/`):

=== "Добавление оценок"

    ```text
    $ curl -i -X POST --data-urlencode "subject=Математика" -d "grade=5" http://127.0.0.1:8080/grades
    HTTP/1.1 303 See Other
    Content-Type: text/html; charset=UTF-8
    Content-Length: 0
    Connection: close
    Location: /

    $ curl -X POST --data-urlencode "subject=Математика" -d "grade=4" http://127.0.0.1:8080/grades
    $ curl -X POST --data-urlencode "subject=Физика" -d "grade=3" http://127.0.0.1:8080/grades
    ```

=== "Журнал (GET /)"

    ```text
    $ curl -s http://127.0.0.1:8080/
    ...
    <table><tr><th>Дисциплина</th><th>Оценки</th><th>Средний балл</th></tr><tr><td>Математика</td><td>5, 4</td><td>4.50</td></tr><tr><td>Физика</td><td>3</td><td>3.00</td></tr></table>
    ...
    ```

=== "Обработка ошибок"

    ```text
    оценка 7              -> 400
    оценка "abc"          -> 400
    нет поля subject      -> 400
    GET /nope             -> 404
    DELETE /              -> 405
    POST /nope            -> 404
    ```

=== "Экранирование"

    ```text
    $ curl -X POST --data-urlencode "subject=<b>XSS</b>" -d "grade=5" http://127.0.0.1:8080/grades
    ...
    <tr><td>&lt;b&gt;XSS&lt;/b&gt;</td><td>5</td><td>5.00</td></tr>
    ...
    ```

---

## Запуск (кратко)

```bash
cd students/K3341/laboratory_works/Degtiar_gleb/laboratory_work_1/task1_udp
python server.py      # терминал 1
python client.py      # терминал 2
```

Остальные задания запускаются так же (`task2_tcp`, `task3_http`, `task4_chat`, `task5_grades`).
Для чата: `python client.py Alice`, `python client.py Bob` и т. д. — по одному терминалу на участника.

## Выводы

В работе реализованы все пять заданий. На практике сравнены два транспортных протокола: UDP отправляет
датаграммы без соединения и без гарантий доставки, TCP устанавливает соединение и передаёт упорядоченный поток байт,
поверх которого приходится самостоятельно определять границы сообщений (в работе — символ `\n` и `Content-Length`).
HTTP оказался обычным текстовым протоколом поверх TCP, который можно разобрать и сформировать вручную. Для
обслуживания нескольких клиентов одновременно использованы потоки (`threading`) и блокировки для защиты общих данных.
