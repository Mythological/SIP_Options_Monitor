# SIP Options Monitor

**English | Русский**

---

## Description (English)

### SIP Options Monitor — SIP Device Availability Monitoring System

This project provides automated monitoring of SIP devices (phones, gateways) by periodically sending SIP OPTIONS requests. If devices become unavailable, notifications are sent via email and/or Telegram, and a summary report is generated at a configurable interval.

#### Main Features:
- Parallel availability checks for a list of SIP devices.
- Flexible configuration of check and reporting intervals.
- Tracks device status and the time of last status change.
- Generates and sends summary email reports and Telegram notifications.
- Uses environment variables for sensitive data configuration.
- Built-in debug mode (verbose output when needed).

#### Dependencies
- Python 3 standard libraries
- [python-dotenv](https://pypi.org/project/python-dotenv/) (for .env support)
- [requests](https://pypi.org/project/requests/) (for Telegram notifications)

#### Quick Start
1. Clone the repository and navigate to the project directory.
2. (Recommended) Create and activate a virtual environment:
   ```
   python3.6 -m venv venv
   source venv/bin/activate
   # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create and configure your `.env` file with SMTP, Telegram, and environment variables (see example below).
5. Run the script:
   ```
   python sip_monitor_en.py
   # or for Russian version:
   python sip_monitor_ru.py
   ```

#### Testing Email and Telegram Notifications
You can test email or Telegram notifications separately by running the corresponding module directly:
```bash
python email_utils.py   # Sends a test email to the specified address
python telegram_utils.py  # Sends a test message to Telegram
```

#### Automatic startup with cron (Linux/macOS)
To run the script automatically at system startup, add it to your crontab with the @reboot flag, specifying the Python path from your virtual environment. Example:

```
# Open crontab for editing
crontab -e

# Add a line (replace the path with your own):
@reboot /path/to/your/project/venv/bin/python /path/to/your/project/sip_monitor_en.py >> /path/to/your/project/monitor.log 2>&1
```

#### Example `.env`
```
# Email settings
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_username
SMTP_PASS=your_password
SENDER_EMAIL=from@example.com
RECIPIENT_EMAIL=to@example.com
ENABLE_EMAIL_ALERTS=True

# Telegram settings
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ENABLE_TELEGRAM_ALERTS=True

# Monitoring settings
DEBUG=True
REPORT_INTERVAL_SECONDS=3600
```

#### File Overview
- `sip_monitor_en.py` — main script (English)
- `sip_monitor_ru.py` — main script (Russian)
- `email_utils.py` — email notification logic
- `telegram_utils.py` — Telegram notification logic
- `requirements.txt` — project dependencies
- `.env` — configuration (do not commit to public repos!)

---

#### Additional tools
You can use the `ip_pinger.py` script to automatically generate a list of IP addresses for SIP devices. This tool scans IP ranges and helps you quickly identify available devices in your network.

---

#### Donate:

BTC: bc1qna64m0wpelkhy3vwhctvpp5g2elsqhj4ykyfgs

ETH: 0x91b86a88c8deb74da72db8743e60f8f6b104e263

USDT TRC20: TFGXNg8GGYQJBAGjZ4bmWHuCTznSmyNqMp

LTC: ltc1qprphmcj7dncdj4k0aucuw43axefyvmdx22tcw5

DOGE: DJmwXWqqmhGy1cSFmgxakP4YhA3PEKksgT

Solana: DmfDLbkHRqhd3LRoGgWpdWLcDAT3dk1wZdSD2sZoGfNe

## License

MIT License

## Описание (Русский)

### SIP Options Monitor — система мониторинга доступности SIP-устройств (телефонов, шлюзов)

Этот проект предназначен для автоматического контроля работоспособности SIP-устройств с помощью периодических SIP OPTIONS-запросов. В случае недоступности устройств отправляются уведомления по email и/или Telegram, а также формируется сводный отчёт с заданным интервалом.

#### Основные функции:
- Параллельная проверка доступности списка SIP-устройств.
- Гибкая настройка интервалов проверки и отчётности.
- Отслеживание состояния устройств и времени последнего изменения статуса.
- Формирование и отправка сводных email-отчётов и Telegram-уведомлений.
- Использование переменных окружения для хранения конфиденциальных данных.
- Встроенный режим отладки (вывод подробных сообщений при необходимости).

#### Зависимости
- Стандартные библиотеки Python 3
- [python-dotenv](https://pypi.org/project/python-dotenv/) (для поддержки .env)
- [requests](https://pypi.org/project/requests/) (для Telegram-уведомлений)

#### Быстрый старт
1. Склонируйте репозиторий и перейдите в каталог проекта.
2. (Рекомендуется) Создайте и активируйте виртуальное окружение:
   ```
   python3.6 -m venv venv
   source venv/bin/activate
   # Для Windows: venv\Scripts\activate
   ```
3. Установите зависимости:
   ```
   pip3.6 install -r requirements.txt
   ```
4. Создайте и настройте файл `.env` с параметрами SMTP, Telegram и переменными окружения (см. пример ниже).
5. Запустите скрипт:
   ```
   python3.6 sip_monitor_ru.py
   ```

#### Проверка email и Telegram уведомлений
Вы можете проверить работу отправки email или Telegram отдельно, запустив соответствующий модуль напрямую:
```bash
python3.6 email_utils.py   # Отправит тестовое письмо на указанный адрес
python3.6 telegram_utils.py  # Отправит тестовое сообщение в Telegram
```

#### Автоматический запуск через cron (Linux/macOS)
Чтобы скрипт запускался автоматически при загрузке системы, добавьте его в crontab с флагом @reboot, указав путь к Python из виртуального окружения. Пример:

```
# Открыть crontab для редактирования
crontab -e

# Добавить строку (замените путь на свой):
@reboot /path/to/your/project/venv/bin/python3.6 /path/to/your/project/sip_monitor_ru.py >> /path/to/your/project/monitor.log 2>&1
```

#### Пример `.env`
```
# Email settings
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_username
SMTP_PASS=your_password
SENDER_EMAIL=from@example.com
RECIPIENT_EMAIL=to@example.com
ENABLE_EMAIL_ALERTS=True

# Telegram settings
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ENABLE_TELEGRAM_ALERTS=True

# Monitoring settings
DEBUG=True
REPORT_INTERVAL_SECONDS=3600
```

#### Краткое описание файлов
- `sip_monitor_ru.py` — основной скрипт на русском языке
- `sip_monitor_en.py` — основной скрипт на английском языке
- `email_utils.py` — отправка email-уведомлений
- `telegram_utils.py` — отправка Telegram-уведомлений
- `requirements.txt` — зависимости проекта
- `.env` — настройки (не добавляйте в публичный репозиторий!)

---

#### Дополнительные инструменты
Для автоматического составления списка IP-адресов SIP-устройств вы можете использовать скрипт `ip_pinger.py`. Он позволяет быстро просканировать диапазон адресов и выявить доступные устройства в вашей сети.

#### Донат:

BTC: bc1qna64m0wpelkhy3vwhctvpp5g2elsqhj4ykyfgs

ETH: 0x91b86a88c8deb74da72db8743e60f8f6b104e263

USDT TRC20: TFGXNg8GGYQJBAGjZ4bmWHuCTznSmyNqMp

LTC: ltc1qprphmcj7dncdj4k0aucuw43axefyvmdx22tcw5

DOGE: DJmwXWqqmhGy1cSFmgxakP4YhA3PEKksgT

Solana: DmfDLbkHRqhd3LRoGgWpdWLcDAT3dk1wZdSD2sZoGfNe

---

## License

MIT License
