import ipaddress
import subprocess
import platform
import threading
import queue
import time

# --- Настройки ---
# Укажите диапазоны IP для сканирования.
# Можно использовать CIDR (например, "192.168.1.0/24")
# или отдельные IP-адреса.
IP_RANGES_TO_SCAN = [
    "172.16.1.0/23",
    "172.16.3.0/23",
]

# Количество одновременных потоков для пинга
MAX_THREADS = 50

# Параметры Ping
PING_TIMEOUT_MS = 1000 # Таймаут ожидания ответа в миллисекундах
PING_COUNT = 3        # Количество отправляемых пакетов

# --- /Настройки ---

def ping_ip(ip_str):
    """
    Отправляет один пинг на указанный IP-адрес.
    Возвращает True, если хост доступен, иначе False.
    """
    param = "-n" if platform.system().lower() == "windows" else "-c"
    timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
    # Для -W в Linux/macOS таймаут указывается в секундах
    timeout_val = str(PING_TIMEOUT_MS) if platform.system().lower() == "windows" else str(PING_TIMEOUT_MS / 1000.0)

    command = ["ping", param, str(PING_COUNT), timeout_param, timeout_val, ip_str]
    # Отладочный вывод команды
    print(f"  [DEBUG PING {ip_str}] Команда: {' '.join(command)}")

    # Добавляем флаги создания для Windows
    startupinfo = None
    creationflags = 0
    if platform.system().lower() == "windows":
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        # Запускаем ping, скрывая вывод в консоль
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                                creationflags=creationflags)
        # Отладочный вывод кода возврата
        print(f"  [DEBUG PING {ip_str}] Код возврата: {result.returncode}")
        # В Windows и Linux/macOS код возврата 0 обычно означает успех
        return result.returncode == 0
    except FileNotFoundError:
        print(f"Ошибка: Команда 'ping' не найдена. Убедитесь, что она доступна в системе.")
        return False
    except Exception as e:
        # Отладочный вывод ошибки
        print(f"  [DEBUG PING {ip_str}] Ошибка: {e}")
        return False

def worker(ip_queue, results_queue):
    """
    Рабочая функция для потока. Берет IP из очереди, пингует
    и кладет результат (если успешно) в другую очередь.
    """
    while not ip_queue.empty():
        try:
            ip = ip_queue.get_nowait()
            ip_str = str(ip) # Преобразуем в строку один раз
        except queue.Empty:
            break # Очередь задач пуста

        # Отладочный вывод перед проверкой
        print(f"[DEBUG WORKER] Проверка IP: {ip_str}")
        ping_result = ping_ip(ip_str)
        print(f"[DEBUG WORKER] Результат ping_ip для {ip_str}: {ping_result}")

        if ping_result:
            print(f"[DEBUG WORKER] IP {ip_str} доступен, добавляем в результаты.")
            results_queue.put(ip_str)
        # else: # Можно добавить вывод для недоступных для полноты картины
        #     print(f"[DEBUG WORKER] IP {ip_str} недоступен.")
        ip_queue.task_done() # Сообщаем, что задача обработана

def main():
    """
    Основная функция скрипта.
    """
    print("Начало сканирования IP-адресов...")
    start_time = time.time()

    ip_tasks_queue = queue.Queue()
    ping_results_queue = queue.Queue()
    total_ips_to_scan = 0

    # Заполняем очередь задач IP-адресами из диапазонов
    print("Обработка диапазонов:")
    for ip_range_str in IP_RANGES_TO_SCAN:
        try:
            network = ipaddress.ip_network(ip_range_str, strict=False)
            print(f"- Сканирование сети: {network} ({network.num_addresses} адресов)")
            for ip in network.hosts(): # .hosts() исключает адрес сети и broadcast
                ip_tasks_queue.put(ip)
                total_ips_to_scan += 1
        except ValueError:
            try:
                 # Пытаемся обработать как отдельный IP
                 ip = ipaddress.ip_address(ip_range_str)
                 print(f"- Сканирование отдельного IP: {ip}")
                 ip_tasks_queue.put(ip)
                 total_ips_to_scan += 1
            except ValueError:
                 print(f"- Ошибка: Неверный формат диапазона или IP: {ip_range_str}")

    if total_ips_to_scan == 0:
        print("Нет IP-адресов для сканирования.")
        return

    print(f"\nВсего IP-адресов для проверки: {total_ips_to_scan}")
    print(f"Запуск пинга с использованием до {MAX_THREADS} потоков...")

    threads = []
    for _ in range(min(MAX_THREADS, total_ips_to_scan)):
        thread = threading.Thread(target=worker, args=(ip_tasks_queue, ping_results_queue), daemon=True)
        threads.append(thread)
        thread.start()

    # Ожидаем завершения всех задач в очереди
    ip_tasks_queue.join()

    # Дополнительное ожидание завершения потоков (на всякий случай)
    for t in threads:
         t.join(timeout=1.0) # Даем потокам немного времени на завершение

    print("\nСканирование завершено.")

    # Собираем результаты
    reachable_ips = []
    while not ping_results_queue.empty():
        reachable_ips.append(ping_results_queue.get_nowait())

    # Сортируем для наглядности (опционально)
    try:
        reachable_ips.sort(key=ipaddress.ip_address)
    except ValueError:
        reachable_ips.sort() # Простая сортировка, если есть не-IP строки (не должно быть)

    end_time = time.time()
    print("-" * 30)
    print(f"Доступные IP-адреса ({len(reachable_ips)}):")
    if reachable_ips:
        # Выводим список
        print(reachable_ips)
        # Или выводим каждый IP на новой строке для лучшей читаемости при большом количестве
        # for ip in reachable_ips:
        #     print(ip)
    else:
        print("Доступных IP-адресов не найдено.")
    print("-" * 30)
    print(f"Время выполнения: {end_time - start_time:.2f} секунд")

if __name__ == "__main__":
    main() 
