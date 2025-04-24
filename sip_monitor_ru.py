"""
Скрипт для мониторинга доступности SIP-устройств (телефонов, шлюзов)
путем периодической отправки SIP OPTIONS запросов.

Основные функции:
- Циклическая отправка SIP OPTIONS запросов на список заданных IP-адресов.
- Использование отдельных сокетов и потоков для каждого запроса для
  параллельной проверки и корректной обработки ответов.
- Отслеживание состояния каждого устройства ('ok', 'failed', 'unknown') и
  времени последнего изменения состояния.
- Формирование и отправка сводного email-отчета (интервал регулируется REPORT_INTERVAL_SECONDS) со списком
  недоступных ('failed') устройств и продолжительностью их недоступности.
- Поддержка отправки email через SMTP с TLS/аутентификацией или без них.
- Настраиваемые параметры:
    - Список целевых IP-адресов (`TARGET_IPS`)
    - Локальный IP-адрес для отправки (`SOURCE_IP`)
    - Порты источника и назначения (`SOURCE_PORT`, `TARGET_PORT`)
    - Интервал проверки (`INTERVAL`)
    - Таймаут ожидания ответа (`RECEIVE_TIMEOUT`)
    - Параметры SMTP-сервера и учетные данные для email-оповещений
      (рекомендуется использовать переменные окружения для пароля).

Зависимости:
- Стандартные библиотеки Python 3
- python-dotenv (для поддержки .env)
- requests (для Telegram-уведомлений)

Использование:
1. Настройте параметры в секциях "Настройки" и "Настройки почты".
   Обязательно укажите корректный `SOURCE_IP` и настройте параметры SMTP,
   если включены email-оповещения (`ENABLE_EMAIL_ALERTS = True`).
   Для безопасности используйте переменные окружения SMTP_USER и SMTP_PASS
   для логина и пароля SMTP.
2. Запустите скрипт: python sip_monitor_ru.py
3. Для остановки нажмите Ctrl+C.
"""
import os
import socket
import time
import uuid
import threading
from email_utils import send_email_alert
from telegram_utils import send_telegram_alert

# Интервал отчетов/уведомлений (секунды)
REPORT_INTERVAL_SECONDS = int(os.environ.get("REPORT_INTERVAL_SECONDS", 3600))  # По умолчанию: 3600 секунд 

# --- Настройки ---
TARGET_IPS = ["172.16.31.144", "192.168.13.101"]
SOURCE_IP = "192.168.1.100" # <-- УКАЖИТЕ ВАШ IP! Пример
SOURCE_PORT = 5084     # Локальный порт для отправки (можно выбрать другой)
TARGET_PORT = 5060     # Стандартный SIP порт
INTERVAL = 10          # Интервал отправки в секундах
USER_AGENT = "Python SIP Monitor"
RECEIVE_TIMEOUT = 2    # Время ожидания ответа в секундах
ENABLE_EMAIL_ALERTS = True   # Включить email-уведомления
ENABLE_TELEGRAM_ALERTS = True  # Включить уведомления в Telegram

# --- /Настройки ---

# Теперь храним словарь словарей: {'ip': {'state': 'unknown'/'ok'/'failed', 'since': timestamp}}
phone_status = {}

DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def create_options_message(target_ip, target_port, source_ip, source_port):
    """Создает текстовое сообщение SIP OPTIONS."""
    call_id = str(uuid.uuid4())
    branch = "z9hG4bK" + str(uuid.uuid4())[:8]
    tag = str(uuid.uuid4())[:8]

    message = (
        f"OPTIONS sip:monitor@{target_ip}:{target_port} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {source_ip}:{source_port};branch={branch};rport\r\n"
        f"Max-Forwards: 70\r\n"
        f"From: <sip:monitor@{source_ip}:{source_port}>;tag={tag}\r\n"
        f"To: <sip:monitor@{target_ip}:{target_port}>\r\n"
        f"Contact: <sip:monitor@{source_ip}:{source_port}>\r\n"
        f"Call-ID: {call_id}\r\n"
        f"CSeq: 1 OPTIONS\r\n"
        f"User-Agent: {USER_AGENT}\r\n"
        f"Accept: application/sdp\r\n"
        f"Content-Length: 0\r\n"
        f"\r\n"
    )
    return message.encode('utf-8')

def send_options(target_ip, source_ip_actual):
    """Отправляет OPTIONS, ожидает ответ, обновляет глобальный статус телефона."""
    global phone_status # Объявляем, что будем использовать и изменять глобальную переменную
    options_message_str = create_options_message(target_ip, TARGET_PORT, source_ip_actual, SOURCE_PORT).decode('utf-8')
    options_message_bytes = options_message_str.encode('utf-8')

    debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Отправка на {target_ip}:{TARGET_PORT} (с {source_ip_actual}:{SOURCE_PORT} в заголовках) ===")
    debug_print(options_message_str.strip())
    debug_print(f"========================================")

    sock = None
    current_run_status = 'unknown' # Статус для этого конкретного запуска

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(options_message_bytes, (target_ip, TARGET_PORT))
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Пакет отправлен {target_ip}. Ожидание ответа ({RECEIVE_TIMEOUT}с)...")

        sock.settimeout(RECEIVE_TIMEOUT)
        try:
            data, addr = sock.recvfrom(2048)
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Получен ответ от {addr} для запроса к {target_ip}")
            debug_print(f"--- Сырые данные ({len(data)} байт) ---")
            try:
                 debug_print(data.decode('utf-8', errors='replace'))
            except Exception:
                 debug_print(data)
            debug_print(f"------------------------------------")

            if addr[0] == target_ip:
                try:
                    response = data.decode('utf-8', errors='ignore')
                    status_line = response.splitlines()[0] if response else "ПУСТОЙ ОТВЕТ"
                    if "SIP/2.0 200 OK" in status_line:
                        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Статус: 200 OK от {target_ip}")
                        current_run_status = 'ok'
                    else:
                        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Статус: Не 200 OK от {target_ip}. Первая строка: {status_line}")
                        current_run_status = 'failed'
                except IndexError:
                     debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка: Не удалось разобрать ответ от {target_ip}")
                     current_run_status = 'failed'
                except Exception as parse_e:
                     debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка обработки ответа от {target_ip}: {parse_e}")
                     current_run_status = 'failed'
            else:
                 debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ПРЕДУПРЕЖДЕНИЕ: Ответ от {addr[0]} получен на сокет, ожидавший ответ от {target_ip}")
                 current_run_status = 'failed'

        except socket.timeout:
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Статус: Нет ответа от {target_ip} (таймаут)")
            current_run_status = 'failed'
        except Exception as e:
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка при получении/обработке ответа от {target_ip}: {e}")
            current_run_status = 'failed'

    except socket.gaierror as e:
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка DNS: Не удалось разрешить имя или адрес {target_ip}: {e}")
        current_run_status = 'failed'
    except OSError as e:
         debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка сокета при отправке/создании для {target_ip}: {e}")
         current_run_status = 'failed'
    except Exception as e:
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Неизвестная ошибка при отправке/получении OPTIONS для {target_ip}: {e}")
        current_run_status = 'failed'
    finally:
        if sock:
            sock.close()

    # --- Обновление статуса в глобальном словаре ---
    previous_status_info = phone_status.get(target_ip, {'state': 'unknown', 'since': None})
    previous_state = previous_status_info['state']

    if current_run_status != previous_state:
        # Записываем новый статус и время его установки
        new_timestamp = time.time()
        debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ИЗМЕНЕНИЕ СТАТУСА: {target_ip} перешел из '{previous_state}' в '{current_run_status}' в {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_timestamp))}.")
        phone_status[target_ip] = {'state': current_run_status, 'since': new_timestamp}
    # Если статус не изменился, ничего не делаем со словарем phone_status

def notify_alert(subject, body, telegram_message=None):
    """
    Отправляет уведомления согласно включённым каналам (email/telegram).
    """
    if ENABLE_EMAIL_ALERTS:
        send_email_alert(subject, body)
    if ENABLE_TELEGRAM_ALERTS and telegram_message:
        send_telegram_alert(telegram_message)

def monitor_loop():
    """Основной цикл мониторинга с отправкой отчетов."""
    global phone_status # Объявляем для инициализации
    # Инициализация словаря статусов при запуске
    phone_status = {ip: {'state': 'unknown', 'since': None} for ip in TARGET_IPS}
    debug_print(f"Инициализация статусов: {phone_status}")
    # Добавляем переменную для времени последнего отчета
    last_report_time = time.time()

    source_ip_actual = SOURCE_IP
    if source_ip_actual == "0.0.0.0" or source_ip_actual == "ВАШ_ЛОКАЛЬНЫЙ_IP": # Проверка на случай, если IP не заменен
        debug_print("Предупреждение: SOURCE_IP не задан или оставлен '0.0.0.0'. Попытка автоопределения...")
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect(("8.8.8.8", 80))
            source_ip_actual = temp_sock.getsockname()[0]
            debug_print(f"Автоматически определен IP-адрес источника: {source_ip_actual}")
            temp_sock.close()
        except OSError as e:
            debug_print(f"Не удалось автоматически определить IP-адрес источника: {e}. Будет использоваться '0.0.0.0'.")
            debug_print("Это может привести к выбору неправильного сетевого интерфейса.")
            source_ip_actual = "0.0.0.0"

    debug_print(f"Монитор запущен. IP-адрес источника для SIP заголовков: {source_ip_actual}:{SOURCE_PORT}")
    debug_print(f"Целевые IP: {', '.join(TARGET_IPS)}")
    debug_print(f"Интервал: {INTERVAL} секунд")
    debug_print("-" * 30)

    try:
        while True:
            threads = []
            start_time = time.time()

            for target_ip in TARGET_IPS:
                # Используем глобальный phone_status, поэтому не передаем его в args
                thread = threading.Thread(target=send_options, args=(target_ip, source_ip_actual))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            elapsed_time = time.time() - start_time
            wait_time = max(0, INTERVAL - elapsed_time)
            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Цикл проверки завершен за {elapsed_time:.2f}с.")
            debug_print(f"Текущие статусы: {phone_status}") # Выводим обновленные статусы

            # --- Логика отчета ---
            current_time = time.time()
            if current_time - last_report_time >= REPORT_INTERVAL_SECONDS:
                debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Проверка для отчета (интервал {REPORT_INTERVAL_SECONDS}с)...")
                failed_phones_report_lines = []
                for ip, status_info in phone_status.items():
                    if status_info['state'] == 'failed':
                        failed_since = status_info['since']
                        if failed_since:
                            duration_seconds = current_time - failed_since
                            # Форматируем продолжительность
                            m, s = divmod(duration_seconds, 60)
                            h, m = divmod(m, 60)
                            duration_str = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
                            failed_since_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(failed_since))
                            failed_phones_report_lines.append(f"- {ip}: недоступен с {failed_since_str} (продолжительность: {duration_str})")
                        else:
                             failed_phones_report_lines.append(f"- {ip}: недоступен (точное время сбоя неизвестно)")

                if failed_phones_report_lines:
                    debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Обнаружены недоступные телефоны. Отправка отчета...")
                    subject = f"SIP Monitor Report: Недоступные телефоны ({time.strftime('%Y-%m-%d %H:%M')})"
                    body = "Следующие SIP телефоны в настоящее время недоступны:\n\n" + "\n".join(failed_phones_report_lines) + "\n\nМонитор продолжает работу."
                    telegram_msg = f"SIP Monitor: Недоступные телефоны:\n" + "\n".join(failed_phones_report_lines)
                    notify_alert(subject, body, telegram_message=telegram_msg)
                else:
                     debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Все отслеживаемые телефоны доступны. Отчет не требуется.")

                last_report_time = current_time # Обновляем время последнего отчета

            # --- /Логика отчета ---

            debug_print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ожидание {wait_time:.2f}с до следующего цикла проверки...")
            debug_print("-" * 30)
            if wait_time > 0:
                time.sleep(wait_time)

    except KeyboardInterrupt:
        debug_print("\nОстановка монитора...")

if __name__ == "__main__":
    monitor_loop()
