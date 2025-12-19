import pyautogui
import time
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
from PIL import ImageGrab
import configparser
import logging
import os
import requests
import subprocess
import json
import ctypes # Импорт для блокировки экрана
import keyboard 

# НОВОЕ: Импортируем функцию создания GUI из контроллера (предполагая, что оба файла находятся в одной папке)
try:
    from arduino_controller import create_arduino_gui, close_arduino_connection, run_script_from_file, stop_script, get_arduino_connection, set_stop_script_flag, send_stop_command
    from script_api import ScriptAPI, execute_python_script_wrapper
    SCRIPT_API_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    SCRIPT_API_AVAILABLE = False
    
    # Заглушка на случай, если arduino_controller.py не найден
    def create_arduino_gui(*args, **kwargs):
        global log_message
        log_message("Не удалось импортировать 'create_arduino_gui' из arduino_controller.py. Убедитесь, что файл существует.", "error")
        messagebox.showerror("Ошибка", "Модуль arduino_controller.py не найден или содержит ошибки.")
    
    def close_arduino_connection():
        pass
    
    def get_arduino_connection():
        return None
    
    def set_stop_script_flag(value):
        pass
    
    def send_stop_command(connection=None):
        return True
    
    def run_script_from_file(script_file_path):
        log_message("Функция run_script_from_file недоступна.", "error")
        return False
    
    def stop_script():
        """Останавливает выполнение скрипта на Arduino"""
        try:
            # 1. Сначала устанавливаем флаг остановки
            set_stop_script_flag(True)
        
            # 2. Затем отправляем команду STOP
            success = send_stop_command()
            if success:
                log_message("Команда STOP отправлена на Arduino и флаг остановки установлен.", "info")
        
            # 3. Даем время на обработку
            time.sleep(0.3)
        
            # 4. Пытаемся отправить RESET для полного сброса
            try:
                from arduino_controller import get_arduino_connection
                conn = get_arduino_connection()
                if conn and conn.is_open:
                    conn.write(b'RESET\n')
                    conn.flush()
                    log_message("Команда RESET отправлена на Arduino.", "info")
            except Exception as e:
                log_message(f"Ошибка при отправке RESET: {e}", "warning")
            
            return True
        except ImportError:
            log_message("Функция stop_script недоступна.", "error")
            return False
        except Exception as e:
            log_message(f"Ошибка остановки скрипта Arduino: {e}", "error")
            return False

# --- Настройка логирования ---
log_file_path = "app_log.log"
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.FileHandler(log_file_path, encoding='utf-8'),
                       logging.StreamHandler()
                   ])
logger = logging.getLogger(__name__)

# --- Глобальные переменные ---
config = configparser.ConfigParser()
running = False
to_village_region = None
to_village_button_image = ''
disconnect_button_image = ''
detection_threshold = 0.8
nickname_image_paths = []
search_region = None

# Сообщения для Telegram (по умолчанию)
telegram_nickname = "@your_telegram_nickname"
telegram_chat_id = ""
message_on_death = "ботоферма сдохла"
message_on_disconnect = "дисконнект Lineage 2"
message_on_nickname = "на нас напали!"
# Новые глобальные переменные для режимов
shutdown_mode_enabled = False
shutdown_delay_minutes = 25
lock_on_death_enabled = False

# НОВЫЕ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ УПРАВЛЕНИЯ ЧЕРЕЗ TELEGRAM
computer_id = ""
last_update_id = 0
telegram_token = ""
# НОВОЕ: Флаг для отслеживания ручной остановки
manual_stop = False
scripts_window = None # Глобальная переменная для окна скриптов/контроллера

# НОВЫЕ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ СКРИПТОВ
arduino_port = "COM3 - USB Serial Device" # Обновление значения по умолчанию
scripts_enabled = False
selected_script_file = ""  # Добавлена переменная для хранения пути к файлу скрипта
arduino_baudrate = "9600"  # Добавлена переменная для скорости соединения
script_type = "txt"  # НОВОЕ: тип скрипта (txt или py)

arduino_script_thread = None
arduino_script_running = False
arduino_api_instance = None  

# --- Конфигурационный файл ---
CONFIG_FILE = 'config.ini'

# ====================== УТИЛИТЫ ======================

def log_message(message, level="info"):
   """
   Выводит сообщение в текстовый виджет консоли и в лог-файл.
   """
   timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
   formatted_message = f"{timestamp} [{level.upper()}]: {message}"
   if 'console' in globals() and console.winfo_exists():
       console.insert(tk.END, formatted_message + "\n")
       console.yview(tk.END)
   getattr(logger, level)(message)

def update_gui_status():
   """
   Обновляет статус программы на GUI.
   """
   if running:
       status_label.config(text="Статус: Работает ✅", fg="green")
       start_button.config(state=tk.DISABLED)
       stop_button.config(state=tk.NORMAL)
   else:
       status_label.config(text="Статус: Остановлен ❌", fg="red")
       start_button.config(state=tk.NORMAL)
       stop_button.config(state=tk.DISABLED)

def update_scripts_button_status():
    """
    Обновляет внешний вид кнопки 'Скрипты' на главном окне.
    Теперь кнопка оформлена как обычная стандартная кнопка GUI.
    """
    global scripts_enabled
    if 'scripts_button' not in globals():
        return

    if scripts_enabled:
        scripts_button.config(
            text="Скрипты",
            bg="#4CAF50",
            fg="white",
            relief=tk.RAISED,
            bd=2
        )
    else:
        scripts_button.config(
            text="Скрипты",
            bg="#f44336",
            fg="white",
            relief=tk.RAISED,
            bd=2
        )

def update_status_indicators():
   """
   Обновляет иконки статуса для изображений и областей поиска.
   """
   # To Village Image
   if to_village_button_image and os.path.exists(to_village_button_image):
       to_village_image_status.config(text="✅", fg="green")
   else:
       to_village_image_status.config(text="❌", fg="red")

   # Disconnect Image
   if disconnect_button_image and os.path.exists(disconnect_button_image):
       disconnect_image_status.config(text="✅", fg="green")
   else:
       disconnect_image_status.config(text="❌", fg="red")

   # Nickname Image(s)
   if nickname_image_paths:
       nickname_image_status.config(text=f"✅ ({len(nickname_image_paths)})", fg="green")
   else:
       nickname_image_status.config(text="❌", fg="red")

   # Общая область поиска
   if search_region:
       search_region_status.config(text="✅", fg="green")
   else:
       search_region_status.config(text="❌", fg="red")

def apply_settings():
   """
   Применяет настройки из полей ввода GUI.
   """
   global detection_threshold, message_on_death, message_on_disconnect, telegram_nickname, telegram_chat_id, shutdown_mode_enabled, message_on_nickname, shutdown_delay_minutes, lock_on_death_enabled, computer_id, telegram_token
   try:
       detection_threshold_val = float(threshold_entry.get())
       if not (0.0 <= detection_threshold_val <= 1.0):
           raise ValueError("Порог должен быть между 0.0 и 1.0")
       detection_threshold = detection_threshold_val
       log_message(f"Порог совпадения установлен: {detection_threshold}", "info")
   except ValueError as e:
       messagebox.showerror("Ошибка", f"Неверное значение порога: {e}")
       threshold_entry.delete(0, tk.END)
       threshold_entry.insert(0, str(detection_threshold))

   try:
       interval_val = float(interval_entry.get())
       if interval_val <= 0:
            raise ValueError("Интервал должен быть больше 0.")
       log_message(f"Интервал проверки установлен: {interval_val} сек.", "info")
   except ValueError as e:
       messagebox.showerror("Ошибка", f"Неверное значение интервала: {e}")
       interval_entry.delete(0, tk.END)
       interval_entry.insert(0, "2")

   try:
       shutdown_delay_val = int(shutdown_delay_entry.get())
       if shutdown_delay_val < 6:
           raise ValueError("Время до выключения должно быть не менее 6 минут.")
       shutdown_delay_minutes = shutdown_delay_val
       log_message(f"Время до выключения установлено: {shutdown_delay_minutes} мин.", "info")
   except ValueError as e:
       messagebox.showerror("Ошибка", f"Неверное значение времени выключения: {e}")
       shutdown_delay_entry.delete(0, tk.END)
       shutdown_delay_entry.insert(0, str(shutdown_delay_minutes))

   message_on_death = death_message_entry.get()
   message_on_disconnect = disconnect_message_entry.get()
   message_on_nickname = nickname_message_entry.get()
   telegram_chat_id = chat_id_entry.get()

   # Чтение ID компьютера
   computer_id = computer_id_entry.get().strip()
   log_message(f"ID компьютера установлен: '{computer_id}'", "info")

   # НОВОЕ: Чтение Токена Telegram
   telegram_token = telegram_token_entry.get().strip()
   if not telegram_token:
       log_message("ВНИМАНИЕ: Токен Telegram не установлен. Управление и уведомления не будут работать!", "warning")
   else:
       log_message(f"Токен Telegram установлен.", "info")

   shutdown_mode_enabled = shutdown_mode_var.get() == 1
   lock_on_death_enabled = lock_on_death_var.get() == 1 # Чтение новой переменной

   update_telegram_nickname()
   save_config()
   update_status_indicators()
   update_scripts_button_status() # Обновление статуса кнопки "Скрипты"

def load_config():
   """
   Загружает конфигурацию из файла config.ini.
   """
   global to_village_button_image, disconnect_button_image, \
          detection_threshold, message_on_death, message_on_disconnect, \
          telegram_nickname, telegram_chat_id, shutdown_mode_enabled, \
          nickname_image_paths, message_on_nickname, search_region, shutdown_delay_minutes, lock_on_death_enabled, computer_id, telegram_token, \
          arduino_port, scripts_enabled, selected_script_file, arduino_baudrate, script_type

   if os.path.exists(CONFIG_FILE):
       config.read(CONFIG_FILE, encoding='utf-8')
       try:
           # Настройки поиска
           to_village_button_image = config.get('Search', 'to_village_button_image', fallback='')
           disconnect_button_image = config.get('Search', 'disconnect_button_image', fallback='')

           search_region_str = config.get('Search', 'search_region', fallback='')
           if search_region_str:
               try:
                   search_region = tuple(map(int, search_region_str.strip('()').split(',')))
               except ValueError:
                   logger.warning("Неверный формат области поиска в config.ini. Будет сброшено.")
                   search_region = None

           detection_threshold = config.getfloat('Search', 'detection_threshold', fallback=0.8)
           threshold_entry.delete(0, tk.END)
           threshold_entry.insert(0, str(detection_threshold))

           interval_entry.delete(0, tk.END)
           interval_entry.insert(0, config.get('Search', 'interval', fallback='2'))

           # Настройки сообщений
           # НОВОЕ: Загрузка Токена Telegram
           telegram_token = config.get('Messages', 'telegram_token', fallback="")
           # Проверка, что элемент существует, перед попыткой вставки
           if 'telegram_token_entry' in globals():
               telegram_token_entry.delete(0, tk.END)
               telegram_token_entry.insert(0, telegram_token)

           # Загрузка ID компьютера
           computer_id = config.get('Messages', 'computer_id', fallback="")
           computer_id_entry.delete(0, tk.END)
           computer_id_entry.insert(0, computer_id)

           telegram_nickname = config.get('Messages', 'telegram_nickname', fallback="@your_telegram_nickname")
           telegram_nickname_entry.delete(0, tk.END)
           telegram_nickname_entry.insert(0, telegram_nickname)
           if not telegram_nickname_entry.get().startswith('@'):
               telegram_nickname_entry.insert(0, '@' + telegram_nickname_entry.get())

           telegram_chat_id = config.get('Messages', 'telegram_chat_id', fallback="")
           chat_id_entry.delete(0, tk.END)
           chat_id_entry.insert(0, telegram_chat_id)

           message_on_death = config.get('Messages', 'on_death', fallback="ботоферма сдохла")
           death_message_entry.delete(0, tk.END)
           death_message_entry.insert(0, message_on_death)

           message_on_disconnect = config.get('Messages', 'on_disconnect', fallback="дисконнект Lineage 2")
           disconnect_message_entry.delete(0, tk.END)
           disconnect_message_entry.insert(0, message_on_disconnect)

           # --- Загрузка настроек ника ---
           nickname_image_paths_json = config.get('Nickname', 'image_paths', fallback='[]')
           nickname_image_paths = json.loads(nickname_image_paths_json)

           message_on_nickname = config.get('Messages', 'on_nickname', fallback="на нас напали!")
           nickname_message_entry.delete(0, tk.END)
           nickname_message_entry.insert(0, message_on_nickname)

           # Загрузка состояния режимов
           shutdown_mode_enabled = config.getboolean('Settings', 'shutdown_mode', fallback=False)
           shutdown_mode_var.set(1 if shutdown_mode_enabled else 0)

           shutdown_delay_minutes = config.getint('Settings', 'shutdown_delay_minutes', fallback=25)
           shutdown_delay_entry.delete(0, tk.END)
           shutdown_delay_entry.insert(0, str(shutdown_delay_minutes))

           lock_on_death_enabled = config.getboolean('Settings', 'lock_on_death', fallback=False) # Чтение новой переменной
           lock_on_death_var.set(1 if lock_on_death_enabled else 0) # Обновление состояния галочки

           # --- НОВОЕ: Загрузка настроек скриптов ---
           arduino_port = config.get('Scripts', 'arduino_port', fallback="COM3 - USB Serial Device")
           scripts_enabled = config.getboolean('Scripts', 'enabled', fallback=False)
           selected_script_file = config.get('Scripts', 'selected_script_file', fallback="")
           arduino_baudrate = config.get('Scripts', 'arduino_baudrate', fallback="9600")
           script_type = config.get('Scripts', 'script_type', fallback="txt")

           logger.info("Конфигурация успешно загружена.")
       except Exception as e:
           logger.error(f"Ошибка загрузки конфигурации: {e}")
   else:
       logger.info("config.ini не найден. Создаем новый.")

def save_config():
   """
   Сохраняет текущую конфигурацию в файл config.ini.
   """
   config['Search'] = {
       'to_village_button_image': to_village_button_image,
       'disconnect_button_image': disconnect_button_image,
       'search_region': str(search_region) if search_region else '',
       'detection_threshold': str(detection_threshold),
       'interval': interval_entry.get()
   }
   config['Messages'] = {
       # НОВОЕ: Сохранение Токена
       'telegram_token': telegram_token_entry.get(),
       'computer_id': computer_id_entry.get(),
       'telegram_nickname': telegram_nickname_entry.get(),
       'telegram_chat_id': chat_id_entry.get(),
       'on_death': death_message_entry.get(),
       'on_disconnect': disconnect_message_entry.get(),
       'on_nickname': nickname_message_entry.get()
   }
   config['Nickname'] = {
       'image_paths': json.dumps(nickname_image_paths)
   }
   config['Settings'] = {
       'shutdown_mode': str(shutdown_mode_var.get() == 1),
       'shutdown_delay_minutes': str(shutdown_delay_minutes),
       'lock_on_death': str(lock_on_death_var.get() == 1) # Сохранение новой переменной
   }
   # НОВОЕ: Секция для скриптов
   config['Scripts'] = {
       'arduino_port': arduino_port,
       'enabled': str(scripts_enabled),
       'selected_script_file': selected_script_file,
       'arduino_baudrate': arduino_baudrate,
       'script_type': script_type
   }
   with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
       config.write(configfile)
   logger.info("Конфигурация успешно сохранена.")

def update_telegram_nickname(event=None):
   """
   Обновляет никнейм Telegram и сохраняет в конфиг.
   Автоматически добавляет '@' если отсутствует.
   """
   current_text = telegram_nickname_entry.get()
   if not current_text.startswith('@'):
       telegram_nickname_entry.delete(0, tk.END)
       telegram_nickname_entry.insert(0, '@' + current_text)
   save_config()

# ====================== TELEGRAM ======================

def get_token():
    """
    Возвращает текущий токен из глобальной переменной.
    """
    global telegram_token
    if not telegram_token:
        log_message("Ошибка: Токен Telegram не установлен.", "error")
    return telegram_token

def send_telegram(text: str, target_chat_id: str = None):
   token = get_token()
   if not token: return False

   url = "https://api.telegram.org/bot"

   channel_id = target_chat_id if target_chat_id else telegram_chat_id

   if not channel_id:
       log_message("Ошибка Telegram: Chat ID пуст. Невозможно отправить сообщение.", "error")
       return False

   url += token
   method = url + "/sendMessage"

   try:
       r = requests.post(method, data={
            "chat_id": channel_id,
            "text": text
             })
       if r.status_code != 200:
           logger.error(f"Telegram API Error: {r.status_code} - {r.text}")
           raise Exception(f"post_text error: {r.status_code} - {r.text}")
       log_message(f"Сообщение в Telegram отправлено: '{text}'", "info")
       return True
   except requests.exceptions.RequestException as e:
       log_message(f"[Telegram Error]: Не удалось отправить сообщение. Ошибка: {e}. Проверьте подключение к интернету и токен.", "error")
       return False
   except Exception as e:
       log_message(f"[Telegram Error - General]: Не удалось отправить сообщение. Ошибка: {e}", "error")
       return False

def send_telegram_photo(text: str, photo_path: str, target_chat_id: str = None):
    """
    Отправляет текстовое сообщение и фото в Telegram.
    """
    token = get_token()
    if not token: return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    channel_id = target_chat_id if target_chat_id else chat_id_entry.get()

    if not channel_id or not photo_path or not os.path.exists(photo_path):
        log_message("Ошибка Telegram: Chat ID или путь к фото недействительны. Сообщение не отправлено.", "error")
        return False

    try:
        with open(photo_path, 'rb') as photo_file:
            files = {'photo': photo_file}
            data = {'chat_id': channel_id, 'caption': text}
            r = requests.post(url, data=data, files=files)
            if r.status_code != 200:
                logger.error(f"Telegram API Error: {r.status_code} - {r.text}")
                raise Exception(f"sendPhoto error: {r.status_code} - {r.text}")
        log_message(f"Сообщение с фото в Telegram отправлено: '{text}'", "info")
        return True
    except requests.exceptions.RequestException as e:
        log_message(f"[Telegram Error]: Не удалось отправить фото. Ошибка: {e}", "error")
        return False
    except Exception as e:
        log_message(f"[Telegram Error - General]: Не удалось отправить фото. Ошибка: {e}", "error")
        return False

# ====================== TELEGRAM УПРАВЛЕНИЕ ======================

def report_status(chat_id_to_reply):
   """
   Отправляет текущий статус программы в Telegram.
   """
   status_text = "Работает ✅" if running else "Остановлен ❌"
   
   report = f"🤖 Статус программы '{computer_id}': {status_text}\n\n"
   report += f"🔎 Область поиска: {'Установлена' if search_region else 'Не установлена'}\n"
   report += f"🔪 To Village (Смерть): {'Установлено' if to_village_button_image else 'Не установлено'}\n"
   report += f"🔌 Дисконнект: {'Установлено' if disconnect_button_image else 'Не установлено'}\n"
   report += f"⚔️ Изображения ника: {len(nickname_image_paths)}\n"
   report += f"⏲️ Интервал проверки: {interval_entry.get()} сек.\n"
   report += f"🛡️ Порог совпадения: {detection_threshold}\n"
   report += f"💡 Режим выключения: {'Включен' if shutdown_mode_var.get() == 1 else 'Выключен'}\n"
   report += f"🔒 Блокировка экрана: {'Включена' if lock_on_death_var.get() == 1 else 'Выключена'}\n"
   report += f"⚙️ Скрипты: {'Включены' if scripts_enabled else 'Выключены'} ({arduino_port})"
   report += f"\n📜 Тип скрипта: {script_type.upper()}"

   send_telegram(report, target_chat_id=chat_id_to_reply)

def process_telegram_command(text, chat_id):
    """
    Парсит и выполняет команды из Telegram.
    """
    global running
    
    # 1. Проверка команды и ID
    command_prefix = text.lower().strip()
    # Удаляем потенциально ведущий слэш для обработки
    if command_prefix.startswith('/'):
        command_prefix = command_prefix[1:]
    
    # Игнорируем суффикс @botname, если он есть.
    if '@' in command_prefix:
        command_prefix = command_prefix.split('@')[0]
        
    expected_suffix = f"_{computer_id.lower()}"
    
    if not computer_id:
         # Отвечать некуда, если ID не установлен
         log_message("ID компьютера не установлен. Пропускаю команду Telegram.", "warning")
         return

    if not command_prefix.endswith(expected_suffix):
        # Команда адресована другому компьютеру или имеет неверный формат
        return

    # Извлекаем действие (start, stop, status, test)
    action = command_prefix.replace(expected_suffix, '')
    
    log_message(f"Получена команда из Telegram: /{action}_{computer_id}", "info")
    
    if action == 'start':
        if not running:
            # Выполнение команды start
            root.after(0, start_button_search_thread)
            time.sleep(1) # Дать время на запуск
            send_telegram(f"✅ Программа '{computer_id}' запущена.", target_chat_id=chat_id)
        else:
            send_telegram(f"ℹ️ Программа '{computer_id}' уже работает.", target_chat_id=chat_id)

    elif action == 'stop':
        if running:
            # Выполнение команды stop
            root.after(0, stop_program)
            time.sleep(1) # Дать время на остановку
            send_telegram(f"🛑 Программа '{computer_id}' остановлена.", target_chat_id=chat_id)
        else:
            send_telegram(f"ℹ️ Программа '{computer_id}' уже остановлена.", target_chat_id=chat_id)

    elif action == 'status':
        # Выполнение команды status
        report_status(chat_id_to_reply=chat_id)

    elif action == 'test':
        # Выполнение команды test. Передаем chat_id для ответа скриншотом.
        root.after(0, lambda: send_test_message(chat_id_to_reply=chat_id)) 
        send_telegram(f"📸 Запущена тестовая отправка скриншота для '{computer_id}'.", target_chat_id=chat_id)

    elif action == 'shutdown':
        # Выполнение команды выключения
        send_telegram(f"🔌 Выполняю выключение компьютера '{computer_id}' через 20 секунд...", target_chat_id=chat_id)
        
        # Запускаем выключение в отдельном потоке
        def shutdown_sequence():
            # Закрываем L2
            close_l2_process()
            time.sleep(20)  # Ждем 20 секунд
            shutdown_computer()
            
        threading.Thread(target=shutdown_sequence).start()

    else:
        # Неизвестная команда
        send_telegram(f"❓ Неизвестная команда для '{computer_id}'. Доступны: /start_{computer_id}, /stop_{computer_id}, /status_{computer_id}, /test_{computer_id}.", target_chat_id=chat_id)

def get_telegram_updates():
    """
    Получает новые обновления (сообщения) от Telegram API.
    """
    global last_update_id
    token = get_token() 
    if not token: return
    
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    # 'offset' используется для пропуска уже обработанных обновлений.
    params = {'timeout': 30, 'offset': last_update_id}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        data = response.json()
        
        if data['ok'] and data['result']:
            for update in data['result']:
                last_update_id = update['update_id'] + 1
                
                if 'message' in update and 'text' in update['message']:
                    text = update['message']['text']
                    chat_id = update['message']['chat']['id']
                    
                    # Обработка команды в отдельном потоке
                    threading.Thread(target=process_telegram_command, args=(text, chat_id)).start()
        
    except requests.exceptions.RequestException as e:
        # Обработка ошибок сети/API. Обычные таймауты пропускаем.
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 409:
            # Логируем 409 как предупреждение, поскольку это ожидаемое поведение при конфликте
            logger.warning(f"[Telegram Polling Error]: HTTP Error 409 Conflict. Убедитесь, что этот токен бота запущен только в одном экземпляре программы.")
        elif not isinstance(e, requests.exceptions.Timeout):
             log_message(f"[Telegram Polling Error]: Network Error: {e}", "warning")


def telegram_listener_logic():
    """
    Основная логика потока прослушивания Telegram.
    """
    log_message("Поток прослушивания Telegram запущен.", "info")
    
    # Инициализация last_update_id для сброса старых сообщений при старте
    try:
        token = get_token()
        if token:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            requests.get(url, params={'timeout': 1, 'offset': -1}, timeout=2)
            log_message("Смещение Telegram обновлений инициализировано.", "info")
    except Exception:
        pass # Игнорируем ошибки при инициализации смещения, опрос продолжится

    
    while root.winfo_exists(): # Проверка, что GUI еще работает
        if telegram_chat_id and computer_id and get_token():
            get_telegram_updates()
        else:
            time.sleep(5) # Ждем, пока пользователь введет Chat ID, Computer ID и Токен
            
        time.sleep(1) # Короткая пауза между опросами
    
    log_message("Поток прослушивания Telegram завершен.", "info")


def start_telegram_listener():
    """
    Запускает поток прослушивания Telegram.
    """
    listener_thread = threading.Thread(target=telegram_listener_logic)
    listener_thread.daemon = True # Поток завершится при закрытии основного приложения
    listener_thread.start()
    log_message("Запуск потока прослушивания Telegram.", "info")


# ====================== ПОИСК ======================

def find_image_in_region(image_path, search_region):
   """
   Ищет изображение по пути image_path в заданной области search_region.
   Возвращает координаты верхнего левого угла найденного изображения и его размеры,
   или (None, None) если не найдено.
   """
   if not search_region or not image_path or not os.path.exists(image_path):
       return None, None

   try:
       template = cv2.imread(image_path, cv2.IMREAD_COLOR)
       if template is None:
           log_message(f"Ошибка: Не удалось загрузить изображение из '{image_path}'. Проверьте путь.", "error")
           return None, None
       
       screenshot = pyautogui.screenshot(region=search_region)
       screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

       result = cv2.matchTemplate(screenshot_np, template, cv2.TM_CCOEFF_NORMED)
       min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

       if max_val >= detection_threshold:
           h, w = template.shape[0], template.shape[1]
           top_left_in_region = max_loc
           top_left_on_screen = (search_region[0] + top_left_in_region[0], search_region[1] + top_left_in_region[1])
           return top_left_on_screen, (w, h)
       
       return None, None
   except Exception as e:
       log_message(f"[Ошибка поиска изображения]: {e}", "error")
       return None, None

def perform_shutdown_sequence():
   """
   Выполняет последовательность закрытия L2 и выключения компьютера
   с задержками, указанными пользователем.
   """
   log_message("Режим выключения активирован: Начинаю последовательность выключения...", "info")
   
   # Останавливаем скрипт Arduino перед началом выключения
   stop_arduino_script_on_event()
   
   delay_before_close = max(0, shutdown_delay_minutes - 5)
   
   log_message(f"Ожидание {delay_before_close} минут перед закрытием L2...", "info")
   time.sleep(delay_before_close * 60)

   log_message("Закрытие процесса L2...", "info")
   close_l2_process()

   log_message("Ожидание 5 минут перед выключением компьютера...", "info")
   time.sleep(5 * 60)

   log_message("Выключение компьютера...", "info")
   shutdown_computer()

def start_search_logic():
   """
   Основная логика поиска кнопок "To Village", "Дисконнект" и изображения ника.
   Запускается в отдельном потоке.
   """
   global running, shutdown_mode_enabled, lock_on_death_enabled
   try:
       log_message("Поток поиска запущен. Начало сканирования заданной области...", "info")
       while running:
           found_event = False
           
           # Проверка дисконнекта
           if disconnect_button_image and search_region:
               found_disconnect_coords, _ = find_image_in_region(disconnect_button_image, search_region)
               if found_disconnect_coords:
                   log_message("Обнаружен дисконнект! Отправляю уведомление.", "info")
                   formatted_message = f"{telegram_nickname_entry.get()} {disconnect_message_entry.get()}"
                   send_telegram(formatted_message)
                   if lock_on_death_enabled:
                       try:
                          ctypes.windll.user32.LockWorkStation()
                          log_message("Экран успешно заблокирован.", "info")
                       except Exception as e:
                          log_message(f"Ошибка при блокировке экрана: {e}", "error")
                   found_event = True
           
           if found_event:
               # ОСТАНОВИТЬ СКРИПТ ARDUINO ПРИ СРАБАТЫВАНИИ
               stop_arduino_script_on_event()
               running = False
               break
               
           # Проверка кнопки "To Village" (смерть)
           if to_village_button_image and search_region:
               found_to_village_coords, _ = find_image_in_region(to_village_button_image, search_region)
               if found_to_village_coords:
                   log_message("Кнопка 'To Village' найдена! Отправляю уведомление.", "info")
                   formatted_message = f"{telegram_nickname_entry.get()} {death_message_entry.get()}"
                   send_telegram(formatted_message)
                   if lock_on_death_enabled:
                       try:
                         ctypes.windll.user32.LockWorkStation()
                         log_message("Экран успешно заблокирован.", "info")
                       except Exception as e:
                          log_message(f"Ошибка при блокировке экрана: {e}", "error")
                   found_event = True
           
           if found_event:
               # ОСТАНОВИТЬ СКРИПТ ARDUINO ПРИ СРАБАТЫВАНИИ
               stop_arduino_script_on_event()
               running = False
               break
               
           # --- ЛОГИКА ПРОВЕРКИ НИКА ---
           if nickname_image_paths and search_region:
               for nick_image_path in nickname_image_paths:
                   found_coords, _ = find_image_in_region(nick_image_path, search_region)
                   if found_coords:
                       log_message(f"Изображение ника найдено! '{os.path.basename(nick_image_path)}'. Запускаю последовательность действий...", "info")
                       
                       # Блокировка экрана Windows
                       try:
                           ctypes.windll.user32.LockWorkStation()
                           log_message("Экран успешно заблокирован.", "info")
                       except Exception as e:
                           log_message(f"Ошибка при блокировке экрана: {e}", "error")

                       formatted_message = f"{telegram_nickname_entry.get()} {nickname_message_entry.get()}"
                       send_telegram(formatted_message)
                       
                       found_event = True
                       break
                       
           if found_event:
               # ОСТАНОВИТЬ СКРИПТ ARDUINO ПРИ СРАБАТЫВАНИИ
               stop_arduino_script_on_event()
               running = False
               break
               
           log_message("Кнопки и ники не найдены. Проверяю снова...", "info")
           time.sleep(float(interval_entry.get()))

   except Exception as e:
       log_message(f"[Глобальная ошибка в потоке поиска]: {e}", "error")
   finally:
       # Проверка на manual_stop, чтобы предотвратить выключение ПК при ручной остановке.
       global manual_stop
       if shutdown_mode_enabled and not manual_stop:
           # ОСТАНОВИТЬ СКРИПТ ARDUINO ПЕРЕД ВЫКЛЮЧЕНИЕМ КОМПЬЮТЕРА
           stop_arduino_script_on_event()
           threading.Thread(target=perform_shutdown_sequence).start()
       log_message("Поток поиска завершен.", "info")
       root.after(100, update_gui_status)

# ====================== СИСТЕМА ЗАПУСКА СКРИПТОВ ======================

def run_arduino_script_wrapper(script_file_path):
    """
    Обертка для запуска скрипта Arduino с возможностью прерывания.
    """
    global arduino_script_running, script_type, arduino_api_instance
    arduino_script_running = True
    arduino_api_instance = None  # Сбрасываем перед запуском
    
    try:
        # Проверяем флаг перед запуском
        if not arduino_script_running:
            log_message("Скрипт Arduino отменен перед запуском.", "info")
            return
            
        log_message(f"Запуск скрипта '{os.path.basename(script_file_path)}' (тип: {script_type})", "info")
        
        if script_type == "py" and SCRIPT_API_AVAILABLE:
            # Запуск Python скрипта через API
            from arduino_controller import get_arduino_connection, set_stop_script_flag
            from script_api import ScriptAPI, execute_python_script_wrapper
            
            conn = get_arduino_connection()
            if conn and conn.is_open:
                # Создаем API инстанс и сохраняем его глобально
                arduino_api_instance = ScriptAPI(
                    conn, 
                    log_message, 
                    lambda: False,  # get_stop_flag (будет управляться из arduino_controller)
                    lambda flag: set_stop_script_flag(flag)
                )
                
                # Сохраняем инстанс API для возможности принудительной остановки
                success = arduino_api_instance.execute_python_script(script_file_path)
                
                if success:
                    log_message(f"Python скрипт '{os.path.basename(script_file_path)}' успешно выполнен.", "info")
                else:
                    log_message(f"Python скрипт '{os.path.basename(script_file_path)}' завершен с ошибкой или остановлен.", "info")
            else:
                log_message("Arduino не подключен. Невозможно выполнить Python скрипт.", "error")
        else:
            # Запуск текстового скрипта (старый метод)
            success = run_script_from_file(script_file_path)
            
            if success:
                log_message(f"Скрипт Arduino '{os.path.basename(script_file_path)}' успешно выполнен.", "info")
            else:
                log_message(f"Ошибка выполнения скрипта Arduino '{os.path.basename(script_file_path)}'.", "error")
    except Exception as e:
        log_message(f"Ошибка в потоке скрипта Arduino: {e}", "error")
    finally:
        arduino_script_running = False
        arduino_api_instance = None  # Очищаем ссылку на API

def start_arduino_script():
    """
    Запускает скрипт Arduino в отдельном потоке.
    """
    global selected_script_file, arduino_script_thread, arduino_script_running, script_type
    
    if not selected_script_file or not os.path.exists(selected_script_file):
        log_message("Файл скрипта не выбран или не существует. Скрипт Arduino не будет запущен.", "warning")
        return
    
    # Определяем тип скрипта по расширению
    file_ext = os.path.splitext(selected_script_file)[1].lower()
    if file_ext == '.py':
        script_type = "py"
        if not SCRIPT_API_AVAILABLE:
            log_message("Script API не доступен. Не могу выполнить Python скрипт.", "error")
            return
    else:
        script_type = "txt"
    
    # Сохраняем тип скрипта в конфиг
    save_config()
    
    # Если скрипт уже запущен, не запускаем снова
    if arduino_script_running:
        log_message("Скрипт Arduino уже выполняется.", "info")
        return
    
    log_message(f"Запуск скрипта Arduino из файла: {os.path.basename(selected_script_file)} (тип: {script_type})", "info")
    
    # Запускаем скрипт в отдельном потоке через обертку
    arduino_script_thread = threading.Thread(target=run_arduino_script_wrapper, args=(selected_script_file,))
    arduino_script_thread.daemon = True
    arduino_script_thread.start()

def stop_arduino_script_on_event():
    """
    Останавливает скрипт Arduino при срабатывании события.
    """
    global arduino_script_thread, arduino_script_running
    
    if arduino_script_running:
        log_message("Сработало событие! Останавливаю скрипт Arduino...", "info")
        
        # 1. Устанавливаем все возможные флаги остановки
        arduino_script_running = False
        set_stop_script_flag(True)
        
        # 2. Если это Python скрипт, используем специальный метод остановки
        if script_type == "py":
            stop_python_script()  # <-- ДОБАВЬТЕ ЭТО
        
        # 3. Многократно отправляем STOP на Arduino
        success_count = 0
        for i in range(3):
            success = send_stop_command()
            if success:
                success_count += 1
            time.sleep(0.1)
        
        log_message(f"Команда STOP отправлена {success_count}/3 раз.", "info")
        
        # 4. Пытаемся отправить RESET для полного сброса
        try:
            from arduino_controller import get_arduino_connection
            conn = get_arduino_connection()
            if conn and conn.is_open:
                conn.write(b'RESET\n')
                conn.flush()
                log_message("Команда RESET отправлена на Arduino.", "info")
        except Exception as e:
            log_message(f"Ошибка при отправке RESET: {e}", "warning")
        
        # 5. Ждем завершения потока
        if arduino_script_thread and arduino_script_thread.is_alive():
            log_message("Ожидание завершения потока скрипта Arduino...", "info")
            
            # Ждем с небольшими интервалами, проверяя статус
            for i in range(10):  # 10 попыток по 0.5 секунды = 5 секунд максимум
                if not arduino_script_thread.is_alive():
                    log_message("Поток скрипта Arduino успешно завершен.", "info")
                    break
                time.sleep(0.5)
                log_message(f"Ожидание... (попытка {i+1}/10)", "info")
            else:
                log_message("ВНИМАНИЕ: Поток скрипта Arduino не завершился за 5 секунд!", "warning")
                log_message("Поток продолжает работу в фоне.", "warning")
                
                # Попытка убить поток
                try:
                    import _thread
                    import ctypes
                    # Это опасная операция, используйте с осторожностью
                    log_message("Попытка принудительной остановки потока...", "warning")
                except:
                    pass
        else:
            log_message("Поток скрипта Arduino уже завершен.", "info")

def toggle_scripts_mode():
    """
    Переключает режим скриптов (вкл/выкл) по правому клику мыши.
    """
    global scripts_enabled
    scripts_enabled = not scripts_enabled
    save_config()
    update_scripts_button_status()
    log_message(f"Режим скриптов переключен на {'ВКЛ' if scripts_enabled else 'ОТКЛ'} (правый клик мыши)", "info")

def stop_python_script():
    """Принудительная остановка Python скрипта через API."""
    global arduino_api_instance
    try:
        if arduino_api_instance:
            from script_api import force_stop_script
            success = force_stop_script(arduino_api_instance)
            if success:
                log_message("Принудительная остановка Python скрипта выполнена", "info")
            return success
        return False
    except Exception as e:
        log_message(f"Ошибка при остановке Python скрипта: {e}", "error")
        return False

def start_button_search_thread():
   """
   Запускает поток поиска кнопок при нажатии на кнопку "Старт".
   Теперь также запускает скрипт Arduino если режим скриптов активирован.
   """
   global running, manual_stop, scripts_enabled
   if running:
       messagebox.showinfo("Информация", "Поиск уже запущен.")
       return

   if not search_region:
       messagebox.showerror("Ошибка", "Пожалуйста, сначала выделите общую область поиска.")
       return
       
   if not telegram_token_entry.get().strip():
       messagebox.showerror("Ошибка", "Сначала введите Токен Telegram Бота и нажмите 'Применить настройки'.")
       return

   if not to_village_button_image:
       messagebox.showerror("Ошибка", "Сначала выберите изображение кнопки 'To Village'.")
       return

   if not disconnect_button_image:
       messagebox.showerror("Ошибка", "Сначала выберите изображение кнопки 'Дисконнект'.")
       return
       
   if not nickname_image_paths:
       messagebox.showerror("Ошибка", "Сначала выберите хотя бы одно изображение для ника.")
       return

   running = True
   manual_stop = False # Сброс флага при старте
   update_gui_status()
   
   # Запускаем основной поток поиска изображений
   search_thread = threading.Thread(target=start_search_logic)
   search_thread.daemon = True
   search_thread.start()
   
   # Если режим скриптов активирован, запускаем скрипт Arduino
   if scripts_enabled:
       start_arduino_script()
   
   log_message("Поиск запущен." + (" Скрипт Arduino запущен." if scripts_enabled else ""), "info")

def browse_image(image_type):
   """
   Открывает диалоговое окно для выбора изображения.
   """
   global to_village_button_image, disconnect_button_image, nickname_image_paths
   if image_type == 'ник':
       file_paths = filedialog.askopenfilenames(title=f"Выберите изображения {image_type} (PNG)", filetypes=[("PNG Files", "*.png")])
       if file_paths:
           nickname_image_paths = list(file_paths)
           log_message(f"Выбрано {len(nickname_image_paths)} изображений для ника.", "info")
       else:
           nickname_image_paths = []
           log_message("Выбор изображений ника отменен.", "info")
   else:
       file_path = filedialog.askopenfilename(title=f"Выберите изображение {image_type} (PNG)", filetypes=[("PNG Files", "*.png")])
       if file_path:
           if image_type == 'To Village':
               to_village_button_image = file_path
               log_message(f"Изображение 'To Village' выбрано: {os.path.basename(to_village_button_image)}", "info")
           elif image_type == 'Дисконнект':
               disconnect_button_image = file_path
               log_message(f"Изображение 'Дисконнект' выбрано: {os.path.basename(disconnect_button_image)}", "info")
       else:
           if image_type == 'To Village':
               to_village_button_image = ''
           elif image_type == 'Дисконнект':
               disconnect_button_image = ''
           log_message(f"Выбор изображения '{image_type}' отменен.", "info")

   save_config()
   update_status_indicators()

def select_search_area():
   """
   Позволяет пользователю выделить общую область на экране для поиска всех кнопок и ника.
   """
   global search_region
   messagebox.showinfo("Инструкция", "Появится окно с изображением экрана. Выделите общую область поиска для всех элементов мышкой и нажмите Enter. Для отмены нажмите 'c'.")

   try:
       img = np.array(ImageGrab.grab())
       img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

       r = cv2.selectROI("Выделите общую область и нажмите Enter", img, fromCenter=False, showCrosshair=True)
       cv2.destroyAllWindows()

       if r[2] > 0 and r[3] > 0:
           selected_region = (int(r[0]), int(r[1]), int(r[2]), int(r[3]))
           search_region = selected_region
           log_message(f"Общая область установлена: {selected_region}", "info")
           save_config()
       else:
           log_message("Выбор общей области отменен или область не выбрана.", "info")
       update_status_indicators()
   except Exception as e:
       log_message(f"Ошибка при выделении общей области: {e}", "error")
       update_status_indicators()

def stop_program():
    """
    Останавливает поток поиска и скрипт Arduino.
    """
    global running, manual_stop
    if not running:
        messagebox.showinfo("Информация", "Поиск не запущен.")
        return
    
    running = False
    manual_stop = True
    
    # 1. Сначала останавливаем основной поиск
    log_message("Остановка основной программы...", "info")
    
    # 2. Останавливаем скрипт Arduino если он запущен
    stop_arduino_script_on_event()
    
    # 3. Дополнительная остановка для Python скриптов
    stop_python_script()
    
    log_message("Программа полностью остановлена.", "info")
    root.after(100, update_gui_status)

def close_l2_process():
   """
   Завершает процесс Lineage 2 (l2.bin).
   """
   try:
       subprocess.run(['taskkill', '/IM', 'l2.bin', '/F'], check=True)
       log_message("Процесс 'l2.bin' успешно завершен.", "info")
   except subprocess.CalledProcessError as e:
       log_message(f"Ошибка при завершении 'l2.bin': {e}. Убедитесь, что процесс 'l2.bin' запущен.", "error")
   except FileNotFoundError:
       log_message("Команда 'taskkill' не найдена. Убедитесь, что она доступна в вашей системе (Windows).", "error")

def shutdown_computer():
   """
   Выключает компьютер.
   """
   try:
       subprocess.run(['shutdown', '/s', '/f', '/t', '0'], check=True)
       log_message("Команда выключения компьютера отправлена.", "info")
   except subprocess.CalledProcessError as e:
       log_message(f"Ошибка при выключении компьютера: {e}", "error")
   except FileNotFoundError:
       log_message("Команда 'shutdown' не найдена. Убедитесь, что она доступна в вашей системе.", "error")

def shutdown_computer_prompt():
   """
   Выключает компьютер с подтверждением.
   """
   if messagebox.askyesno("Выключение компьютера", "Вы уверены, что хотите выключить компьютер немедленно? Все несохраненные данные будут утеряны!"):
       shutdown_computer()

# ====================== УПРАВЛЕНИЕ СКРИПТАМИ ======================
def open_scripts_settings():
    """
    Открывает/закрывает окно настроек скриптов.
    """
    global scripts_window, arduino_port, scripts_enabled, selected_script_file, arduino_baudrate, script_type

    if scripts_window and scripts_window.winfo_exists():
        scripts_window.destroy()
        scripts_window = None
    else:
        scripts_window = tk.Toplevel(root)
        scripts_window.title("Настройки скриптов/Arduino")
        scripts_window.geometry("400x550")  # Увеличил высоту для новых элементов
        scripts_window.resizable(False, False)

        root.update_idletasks()
        root_x = root.winfo_x()
        root_y = root.winfo_y()
        root_width = root.winfo_width()

        new_x = root_x + root_width + 10
        new_y = root_y

        scripts_window.geometry(f"+{new_x}+{new_y}")

        def on_scripts_close():
            global scripts_window
            scripts_window.destroy()
            scripts_window = None

        scripts_window.protocol("WM_DELETE_WINDOW", on_scripts_close)

        # Передаем функцию для получения текущего соединения
        def get_current_connection():
            from arduino_controller import get_arduino_connection
            return get_arduino_connection()

        main_module_globals = {
            'arduino_port': arduino_port,
            'scripts_enabled': scripts_enabled,
            'selected_script_file': selected_script_file,
            'arduino_baudrate': arduino_baudrate,
            'arduino_connected': get_current_connection() is not None,
            'script_type': script_type  # Добавляем тип скрипта
        }

        def update_scripts_button_status_wrapper():
            nonlocal main_module_globals
            global arduino_port, scripts_enabled, selected_script_file, arduino_baudrate, script_type
            try:
                arduino_port = main_module_globals.get('arduino_port', arduino_port)
                scripts_enabled = main_module_globals.get('scripts_enabled', scripts_enabled)
                selected_script_file = main_module_globals.get('selected_script_file', selected_script_file)
                arduino_baudrate = main_module_globals.get('arduino_baudrate', arduino_baudrate)
                script_type = main_module_globals.get('script_type', script_type)
            except Exception as e:
                log_message(f"Ошибка при копировании значений из окна скриптов: {e}", "error")
            update_scripts_button_status()

        create_arduino_gui(
            scripts_window, 
            log_message, 
            save_config, 
            update_scripts_button_status_wrapper, 
            main_module_globals
        )

        arduino_port = main_module_globals.get('arduino_port', arduino_port)
        scripts_enabled = main_module_globals.get('scripts_enabled', scripts_enabled)
        selected_script_file = main_module_globals.get('selected_script_file', selected_script_file)
        arduino_baudrate = main_module_globals.get('arduino_baudrate', arduino_baudrate)
        script_type = main_module_globals.get('script_type', script_type)

        update_scripts_button_status()

# ====================== ФУНКЦИЯ ТЕСТИРОВАНИЯ ======================

def send_test_message(chat_id_to_reply: str = None):
    if not search_region:
        messagebox.showerror("Ошибка", "Сначала выделите общую область поиска.")
        return
        
    try:
        # Делаем скриншот общей области и сохраняем его
        screenshot = pyautogui.screenshot(region=search_region)
        screenshot_path = f"test_screenshot_{int(time.time())}.png"
        screenshot.save(screenshot_path)
        
        # Формируем сообщение с текущими настройками
        test_message = f"Тестовое сообщение от бота '{computer_id}'.\n\n"
        test_message += "Текущие настройки:\n"
        test_message += f"- Область поиска: {search_region}\n"
        test_message += f"- Порог совпадения: {detection_threshold}\n"
        
        # Логика сценариев
        test_message += "\nСценарии:\n"
        
        # Сценарий "смерть"
        if to_village_button_image and os.path.exists(to_village_button_image):
            action_on_death = "блокировка экрана" if lock_on_death_var.get() == 1 else "нет"
            test_message += f"- Сценарий 'Смерть' активен. Действие: {action_on_death}. Сообщение: '{death_message_entry.get()}'\n"
        else:
            test_message += "- Сценарий 'Смерть' не настроен.\n"
            
        # Сценарий "дисконнект"
        if disconnect_button_image and os.path.exists(disconnect_button_image):
            action_on_disconnect = "блокировка экрана" if lock_on_death_var.get() == 1 else "нет"
            test_message += f"- Сценарий 'Дисконнект' активен. Действие: {action_on_disconnect}. Сообщение: '{disconnect_message_entry.get()}'\n"
        else:
            test_message += "- Сценарий 'Дисконнект' не настроен.\n"
            
        # Сценарий "найден ник"
        if nickname_image_paths:
            test_message += f"- Сценарий 'Найден ник' активен. Действие: блокировка экрана. Сообщение: '{nickname_message_entry.get()}'\n"
        else:
            test_message += "- Сценарий 'Найден ник' не настроен.\n"
            
        # Режим выключения
        if shutdown_mode_var.get() == 1:
            test_message += f"- Режим выключения включен. Выключение через {shutdown_delay_entry.get()} минут после срабатывания сценария.\n"
        else:
            test_message += "- Режим выключения выключен.\n"
            
        # Скрипты
        if scripts_enabled:
            test_message += f"- Скрипты: Включены (тип: {script_type})\n"
            if selected_script_file:
                test_message += f"  Файл скрипта: {os.path.basename(selected_script_file)}\n"
        else:
            test_message += "- Скрипты: Выключены\n"
            
        # Отправка (Используем target_chat_id)
        send_telegram_photo(test_message, screenshot_path, target_chat_id=chat_id_to_reply)
        
        # Удаление временного файла
        os.remove(screenshot_path)
    
    except Exception as e:
        log_message(f"Ошибка при выполнении тестового сообщения: {e}", "error")


def on_closing():
    """
    Обработчик события закрытия окна GUI.
    Закрывает соединение с Arduino только при закрытии всего приложения.
    """
    global running, scripts_window, arduino_script_running
    running = False
    
    # Удаляем горячие клавиши
    try:
        keyboard.unhook_all()
    except:
        pass
    
    # Останавливаем скрипт Arduino перед закрытием
    stop_arduino_script_on_event()
    stop_python_script()  
    
    # Закрываем соединение с Arduino
    close_arduino_connection()
    # Закрываем окно скриптов, если оно открыто
    if scripts_window and scripts_window.winfo_exists():
        scripts_window.destroy()
    save_config()
    root.destroy()

# --- Настройка GUI ---
root = tk.Tk()
root.title("Save Money")
# Ширина 480 пикселей для корректного размещения трех кнопок
root.geometry("480x920") 
root.resizable(False, False)

# Настройка горячих клавиш
def setup_hotkeys():
    try:
        # Ctrl+Alt+S для старта
        keyboard.add_hotkey('ctrl+alt+s', start_button_search_thread)
        # Ctrl+Alt+Q для остановки
        keyboard.add_hotkey('ctrl+alt+q', stop_program)
        log_message("Горячие клавиши настроены: Ctrl+Alt+S - Старт, Ctrl+Alt+Q - Стоп", "info")
    except Exception as e:
        log_message(f"Ошибка настройки горячих клавиш: {e}. Установите библиотеку keyboard: pip install keyboard", "error")

# Вызываем настройку горячих клавиш
setup_hotkeys()

# Фрейм для общих настроек
settings_frame = tk.LabelFrame(root, text="Общие настройки", padx=10, pady=5)
settings_frame.pack(pady=5, padx=10, fill=tk.X)

tk.Label(settings_frame, text="Интервал проверки (сек.):").grid(row=0, column=0, sticky="w", pady=1)
interval_entry = tk.Entry(settings_frame, width=10)
interval_entry.grid(row=0, column=1, sticky="w", pady=1, padx=5)
interval_entry.insert(0, "2")

tk.Label(settings_frame, text="Порог совпадения (0.0-1.0):").grid(row=1, column=0, sticky="w", pady=1)
threshold_entry = tk.Entry(settings_frame, width=10)
threshold_entry.grid(row=1, column=1, sticky="w", pady=1, padx=5)
threshold_entry.insert(0, "0.8")

# Новый переключатель для режима выключения
shutdown_mode_var = tk.IntVar()
shutdown_mode_checkbutton = tk.Checkbutton(settings_frame, text="Включить режим 'С выключением'", variable=shutdown_mode_var, command=save_config)
shutdown_mode_checkbutton.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

# Новое поле для ввода времени выключения
tk.Label(settings_frame, text="Выключить через (мин.):").grid(row=3, column=0, sticky="w", pady=1)
shutdown_delay_entry = tk.Entry(settings_frame, width=10)
shutdown_delay_entry.grid(row=3, column=1, sticky="w", pady=1, padx=5)
shutdown_delay_entry.insert(0, "25")

# Новый переключатель для блокировки экрана
lock_on_death_var = tk.IntVar()
lock_on_death_checkbutton = tk.Checkbutton(settings_frame, text="Блокировать экран при смерти/дисконнекте", variable=lock_on_death_var, command=save_config)
lock_on_death_checkbutton.grid(row=4, column=0, columnspan=2, sticky="w", pady=5)

tk.Button(settings_frame, text="Применить настройки", command=apply_settings).grid(row=5, column=0, columnspan=2, pady=5)

# Фрейм для управления поиском
search_control_frame = tk.LabelFrame(root, text="Настройки поиска", padx=10, pady=5)
search_control_frame.pack(pady=5, padx=10, fill=tk.X)

# Общая область поиска
tk.Label(search_control_frame, text="Общая область поиска:").grid(row=0, column=0, sticky="w", pady=1)
search_region_status = tk.Label(search_control_frame, text="❌", fg="red", font=("Arial", 14, "bold"))
search_region_status.grid(row=0, column=1, sticky="w", padx=5)
tk.Button(search_control_frame, text="Выделить область", command=select_search_area).grid(row=0, column=2, pady=1)

# To Village (смерть)
tk.Label(search_control_frame, text="Изображение 'To Village':").grid(row=1, column=0, sticky="w", pady=1)
to_village_image_status = tk.Label(search_control_frame, text="❌", fg="red", font=("Arial", 14, "bold"))
to_village_image_status.grid(row=1, column=1, sticky="w", padx=5)
tk.Button(search_control_frame, text="Выбрать", command=lambda: browse_image('To Village')).grid(row=1, column=2, pady=1)

# Дисконнект
tk.Label(search_control_frame, text="Изображение 'Дисконнект':").grid(row=2, column=0, sticky="w", pady=1)
disconnect_image_status = tk.Label(search_control_frame, text="❌", fg="red", font=("Arial", 14, "bold"))
disconnect_image_status.grid(row=2, column=1, sticky="w", padx=5)
tk.Button(search_control_frame, text="Выбрать", command=lambda: browse_image('Дисконнект')).grid(row=2, column=2, pady=1)

# Изображение ника
tk.Label(search_control_frame, text="Изображение ника:").grid(row=3, column=0, sticky="w", pady=1)
nickname_image_status = tk.Label(search_control_frame, text="❌", fg="red", font=("Arial", 14, "bold"))
nickname_image_status.grid(row=3, column=1, sticky="w", padx=5)
tk.Button(search_control_frame, text="Выбрать", command=lambda: browse_image('ник')).grid(row=3, column=2, pady=1)

# Фрейм для сообщений Telegram
messages_frame = tk.LabelFrame(root, text="Сообщения Telegram", padx=10, pady=5)
messages_frame.pack(pady=5, padx=10, fill=tk.X)

# НОВОЕ ПОЛЕ ВВОДА ДЛЯ ТОКЕНА
tk.Label(messages_frame, text="Токен Telegram Бота:").grid(row=0, column=0, sticky="w", pady=1)
telegram_token_entry = tk.Entry(messages_frame, width=36)
telegram_token_entry.grid(row=0, column=1, sticky="ew", pady=1, padx=5)

# НОВОЕ ПОЛЕ ВВОДА ДЛЯ ID КОМПЬЮТЕРА (сдвинуто на 1 строку)
tk.Label(messages_frame, text="ID Компьютера:").grid(row=1, column=0, sticky="w", pady=1)
computer_id_entry = tk.Entry(messages_frame, width=36)
computer_id_entry.grid(row=1, column=1, sticky="ew", pady=1, padx=5)

tk.Label(messages_frame, text="Chat ID Telegram:").grid(row=2, column=0, sticky="w", pady=1)
chat_id_entry = tk.Entry(messages_frame, width=36)
chat_id_entry.grid(row=2, column=1, sticky="ew", pady=1, padx=5)

tk.Label(messages_frame, text="Никнейм для Telegram:").grid(row=3, column=0, sticky="w", pady=1)
telegram_nickname_entry = tk.Entry(messages_frame, width=36)
telegram_nickname_entry.grid(row=3, column=1, sticky="ew", pady=1, padx=5)
telegram_nickname_entry.insert(0, "@")
telegram_nickname_entry.bind("<KeyRelease>", update_telegram_nickname)

tk.Label(messages_frame, text="Сообщение при смерти:").grid(row=4, column=0, sticky="w", pady=1)
death_message_entry = tk.Entry(messages_frame, width=36)
death_message_entry.grid(row=4, column=1, sticky="ew", pady=1, padx=5)
death_message_entry.insert(0, "ботоферма сдохла")

tk.Label(messages_frame, text="Сообщение при дисконнекте:").grid(row=5, column=0, sticky="w", pady=1)
disconnect_message_entry = tk.Entry(messages_frame, width=36)
disconnect_message_entry.grid(row=5, column=1, sticky="ew", pady=1, padx=5)
disconnect_message_entry.insert(0, "дисконнект Lineage 2")

tk.Label(messages_frame, text="Сообщение при смене ника:").grid(row=6, column=0, sticky="w", pady=1)
nickname_message_entry = tk.Entry(messages_frame, width=36)
nickname_message_entry.grid(row=6, column=1, sticky="ew", pady=1, padx=5)
nickname_message_entry.insert(0, "на нас напали!")

status_label = tk.Label(root, text="Статус: Остановлен", font=("Arial", 12, "bold"), fg="red")
status_label.pack(pady=10)

# --- Кнопки Старт/Остановить/Тест ---
button_frame = tk.Frame(root)
button_frame.pack(pady=5)

# Ширина всех 6 кнопок установлена в 15
BUTTON_WIDTH = 15

start_button = tk.Button(button_frame, text="Старт", command=start_button_search_thread, width=BUTTON_WIDTH, height=2, font=("Arial", 10, "bold"))
start_button.pack(side=tk.LEFT, padx=5)
stop_button = tk.Button(button_frame, text="Остановить", command=stop_program, width=BUTTON_WIDTH, height=2, state=tk.DISABLED, font=("Arial", 10, "bold"))
stop_button.pack(side=tk.LEFT, padx=5)
# Новая кнопка "Тест"
test_button = tk.Button(button_frame, text="Тест", command=lambda: send_test_message(), width=BUTTON_WIDTH, height=2, font=("Arial", 10, "bold"))
test_button.pack(side=tk.LEFT, padx=5)

# Фрейм для кнопок управления в одну строку
control_buttons_frame = tk.Frame(root)
control_buttons_frame.pack(pady=5)

# 1. Закрыть L2
tk.Button(control_buttons_frame, text="Закрыть L2", command=close_l2_process, width=BUTTON_WIDTH, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
# 2. Выключить ПК
tk.Button(control_buttons_frame, text="Выключить ПК", command=shutdown_computer_prompt, width=BUTTON_WIDTH, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
# 3. Кнопка "Скрипты" (ранее "Контроллер"), сохраняем ссылку для обновления
scripts_button = tk.Button(control_buttons_frame, text="Скрипты", command=open_scripts_settings, width=BUTTON_WIDTH, font=("Arial", 10, "bold"))
# НОВОЕ: Добавляем обработчик правой кнопки мыши
scripts_button.bind("<Button-3>", lambda event: toggle_scripts_mode())
scripts_button.pack(side=tk.LEFT, padx=5)

# Фрейм для консоли логов
console_frame = tk.LabelFrame(root, text="Логи", padx=10, pady=5)
console_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

# Изменена высота и добавлен шрифт
console = tk.Text(console_frame, height=12, width=70, wrap=tk.WORD, state='normal', font=("Arial", 8))
console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar = tk.Scrollbar(console_frame, command=console.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
console.config(yscrollcommand=scrollbar.set)

root.protocol("WM_DELETE_WINDOW", on_closing)

# Загружаем конфигурацию после создания элементов GUI, чтобы вставить значения
load_config()

# Обновление глобального токена после загрузки конфига (поскольку load_config вызывается перед apply_settings)
telegram_token = telegram_token_entry.get().strip()

update_telegram_nickname()
update_status_indicators()
update_gui_status()
update_scripts_button_status() # НОВОЕ: Обновление статуса кнопки "Скрипты"

# НОВЫЙ ВЫЗОВ: Запуск прослушивания Telegram
start_telegram_listener()

root.mainloop()
