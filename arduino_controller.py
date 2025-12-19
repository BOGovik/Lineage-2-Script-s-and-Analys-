import tkinter as tk
from tkinter import messagebox, filedialog
import time
import threading
import os

# Реальный импорт для работы с COM-портами
try:
    import serial.tools.list_ports
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    class MockSerial:
        def __init__(self, port, baudrate, timeout): pass
        def write(self, data): pass
        def close(self): pass
        def is_open(self): return False
    serial = type('serial', (object,), {'Serial': MockSerial})

# Импорт Script API
try:
    from script_api import ScriptAPI, execute_python_script_wrapper
    SCRIPT_API_AVAILABLE = True
except ImportError:
    SCRIPT_API_AVAILABLE = False

# Глобальные переменные для этого модуля
log_func = None
global_context = {}
arduino_connection = None
baud_rate_var = None
script_file_var = None
connection_status_label = None
port_var = None
is_connection_closing = False
stop_script_flag = False  # Флаг для остановки выполнения скрипта

def set_stop_script_flag(value):
    """Устанавливает флаг остановки скрипта"""
    global stop_script_flag
    stop_script_flag = value

def reset_stop_script_flag():
    """Сбрасывает флаг остановки скрипта"""
    global stop_script_flag
    stop_script_flag = False

# --- Константы ---
BAUD_RATES = [9600, 19200, 38400, 57600, 115200]

# --- Функции для работы с COM-портами ---

def list_serial_ports():
    if not SERIAL_AVAILABLE:
        return ["Нет доступных портов (Установите pyserial)"]

    ports = serial.tools.list_ports.comports()
    if ports:
        return [f"{p.device} - {p.description}" for p in ports]
    else:
        return ["Нет доступных портов"]

def get_port_name(port_str):
    if not port_str:
        return ''
    return port_str.split(' ')[0]

def arduino_connect(port, baudrate_str):
    global log_func, arduino_connection, global_context, is_connection_closing

    if not SERIAL_AVAILABLE:
        log_func("Ошибка: Библиотека 'pyserial' не установлена.", "error")
        messagebox.showerror("Ошибка", "Библиотека 'pyserial' не найдена. Установите ее командой 'pip install pyserial'.")
        global_context['arduino_connected'] = False
        update_connection_status()
        return False

    port_name = get_port_name(port)
    try:
        baudrate = int(baudrate_str)
    except ValueError:
        log_func(f"Ошибка: Некорректная скорость ({baudrate_str}).", "error")
        messagebox.showerror("Ошибка", "Некорректно указана скорость соединения (Baud Rate).")
        global_context['arduino_connected'] = False
        update_connection_status()
        return False

    if not port_name:
        log_func("Ошибка: Пустой порт для подключения.", "error")
        messagebox.showerror("Ошибка", "Выбран пустой порт.")
        global_context['arduino_connected'] = False
        update_connection_status()
        return False

    # Проверяем, не пытаемся ли мы подключиться к тому же порту с той же скоростью
    if arduino_connection and hasattr(arduino_connection, 'port'):
        current_port = getattr(arduino_connection, 'port', '')
        current_baudrate = getattr(arduino_connection, 'baudrate', 0)
        
        if current_port == port_name and current_baudrate == baudrate:
            # Уже подключены к тому же порту с той же скоростью
            log_func(f"Уже подключено к {port_name} со скоростью {baudrate}.", "info")
            global_context['arduino_connected'] = True
            update_connection_status()
            return True

    # Закрываем предыдущее соединение только если оно активно
    if arduino_connection:
        try:
            if arduino_connection.is_open:
                arduino_connection.close()
                log_func(f"Предыдущее соединение закрыто.", "info")
        except Exception as e:
            log_func(f"Ошибка при закрытии предыдущего соединения: {e}", "error")
        arduino_connection = None

    log_func(f"Попытка подключения к Arduino на порту: {port_name} со скоростью {baudrate}...", "info")
    try:
        arduino_connection = serial.Serial(port_name, baudrate, timeout=1)
        time.sleep(2)  # Даем время на инициализацию

        arduino_connection.reset_input_buffer()
        arduino_connection.reset_output_buffer()

        log_func(f"Успешное подключение к Arduino на {port_name} со скоростью {baudrate}!", "info")
                
        global_context['arduino_connected'] = True
        global_context['arduino_port'] = port
        global_context['arduino_baudrate'] = baudrate_str
        update_connection_status()
        return True
    except Exception as e:
        log_func(f"Ошибка подключения к Arduino: {e}", "error")
        messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к {port_name} со скоростью {baudrate}. Ошибка: {e}")
        global_context['arduino_connected'] = False
        update_connection_status()
        return False

def update_connection_status():
    global connection_status_label, arduino_connection, global_context
    
    if connection_status_label is not None:
        if global_context.get('arduino_connected') and arduino_connection and hasattr(arduino_connection, 'is_open'):
            connection_status_label.config(text="Статус: Подключено ✅", fg="green")
        else:
            connection_status_label.config(text="Статус: Не подключено ❌", fg="red")
            global_context['arduino_connected'] = False

def get_arduino_connection():
    """Возвращает текущее соединение с Arduino (для использования в основном модуле)"""
    global arduino_connection
    return arduino_connection

def close_arduino_connection():
    """Закрывает соединение с Arduino только при закрытии основного приложения"""
    global arduino_connection, is_connection_closing
    is_connection_closing = True
    if arduino_connection:
        try:
            arduino_connection.close()
            if log_func:
                log_func(f"Соединение с Arduino закрыто.", "info")
        except Exception as e:
            if log_func:
                log_func(f"Ошибка при закрытии соединения с Arduino: {e}", "error")
        finally:
            arduino_connection = None
    is_connection_closing = False

# --- Функции для работы со скриптами ---

def run_script_from_file(script_file_path, connection=None):
    """Читает и выполняет скрипт из файла путем отправки команд на Arduino"""
    global log_func, arduino_connection, stop_script_flag
    
    # Сбрасываем флаг при начале выполнения
    reset_stop_script_flag()
    
    conn = connection or arduino_connection
    if not conn or not conn.is_open:
        log_func("Ошибка: Arduino не подключен или соединение разорвано.", "error")
        return False

    if not os.path.exists(script_file_path):
        log_func(f"Ошибка: Файл скрипта не найден: {script_file_path}", "error")
        return False

    try:
        with open(script_file_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        log_func(f"Выполнение скрипта '{os.path.basename(script_file_path)}' начато.", "info")
        
        # Сброс состояния Arduino
        try:
            conn.write(b'RESET\n')
            conn.flush()
            time.sleep(0.2)
            conn.reset_input_buffer()
            conn.reset_output_buffer()
        except Exception as e:
            log_func(f"Ошибка сброса Arduino: {e}", "error")
            return False
        
        script_lines = [line.strip() for line in script_content.split('\n')]
        
        # Стек для хранения позиций начала блоков повторений
        repeat_blocks_stack = []
        repeat_counts_stack = []
        repeat_current_counts_stack = []
        
        # Позиция начала LOOP (для бесконечного цикла)
        loop_start_position = -1
        in_loop_mode = False
        
        current_line = 0
        total_lines = len(script_lines)
        
        # Основной цикл выполнения скрипта
        while current_line < total_lines and not stop_script_flag:
            line = script_lines[current_line]
            current_line += 1
            
            # Проверяем флаг остановки
            if stop_script_flag:
                log_func("Флаг остановки установлен. Прерываю выполнение.", "info")
                break
                
            # Проверяем соединение
            if not conn or not conn.is_open:
                log_func("Соединение с Arduino потеряно.", "error")
                return False
            
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith('#'):
                continue
            
            # Обработка команды LOOP_START
            if line == 'LOOP_START':
                if loop_start_position == -1:
                    loop_start_position = current_line
                    in_loop_mode = True
                    log_func("LOOP_START: Начало бесконечного цикла", "info")
                continue
            
            # Обработка команды LOOP_END
            if line == 'LOOP_END':
                if loop_start_position != -1 and in_loop_mode:
                    # Возвращаемся к началу цикла
                    current_line = loop_start_position
                    log_func("LOOP_END: Возврат к началу цикла", "info")
                    continue
                else:
                    log_func("LOOP_END: Вне цикла", "info")
                continue
            
            # Обработка команды REPEAT_START_X
            if line.startswith('REPEAT_START_'):
                try:
                    # Извлекаем количество повторений
                    count_str = line.split('_')[-1]
                    repeat_count = int(count_str)
                    
                    # Сохраняем текущую позицию для возврата
                    repeat_blocks_stack.append(current_line)
                    repeat_counts_stack.append(repeat_count)
                    repeat_current_counts_stack.append(0)
                    
                    log_func(f"Начало блока повторений: {repeat_count} раз(а)", "info")
                except (ValueError, IndexError):
                    log_func(f"Ошибка в команде REPEAT_START: {line}", "warning")
                continue
            
            # Обработка команды REPEAT_END
            if line == 'REPEAT_END':
                if repeat_blocks_stack:
                    # Увеличиваем счетчик текущего блока
                    repeat_current_counts_stack[-1] += 1
                    current_count = repeat_current_counts_stack[-1]
                    total_needed = repeat_counts_stack[-1]
                    
                    if current_count < total_needed:
                        # Возвращаемся к началу блока
                        current_line = repeat_blocks_stack[-1]
                        log_func(f"Повтор блока: {current_count}/{total_needed}", "info")
                    else:
                        # Завершили все повторения, выходим из блока
                        repeat_blocks_stack.pop()
                        repeat_counts_stack.pop()
                        repeat_current_counts_stack.pop()
                        log_func(f"Блок повторений завершен: {total_needed} раз(а)", "info")
                else:
                    log_func("Ошибка: REPEAT_END без соответствующего REPEAT_START", "warning")
                continue
            
            # Обработка команды WAIT
            if line.startswith('WAIT_'):
                try:
                    wait_time_str = line.split('_')[1]
                    wait_time = float(wait_time_str)
                    
                    # Выполняем ожидание с проверкой флага каждые 0.1 секунды
                    total_wait_seconds = wait_time
                    check_intervals = int(total_wait_seconds * 10)
                    
                    for i in range(check_intervals):
                        if stop_script_flag:
                            log_func("Флаг остановки во время ожидания. Прерываю.", "info")
                            break
                        time.sleep(0.1)
                    
                    if stop_script_flag:
                        break
                    continue
                except (ValueError, IndexError):
                    log_func(f"Ошибка в команде WAIT: {line}", "warning")
                    continue
            
            # Отправляем команду на Arduino
            try:
                command = f'{line}\n'
                conn.write(command.encode('utf-8'))
                conn.flush()
                time.sleep(0.02)

                if current_line % 50 == 0:  # Каждые 50 команд
                    conn.reset_input_buffer()
                
                # Проверяем флаг после отправки каждой команды
                if stop_script_flag:
                    log_func("Флаг остановки после отправки команды. Прерываю.", "info")
                    break
            except Exception as e:
                log_func(f"Ошибка отправки команды '{line}': {e}", "error")
                return False
        
        if stop_script_flag:
            log_func(f"Выполнение скрипта '{os.path.basename(script_file_path)}' прервано.", "info")
        else:
            log_func(f"Скрипт '{os.path.basename(script_file_path)}' завершен.", "info")
        return True
        
    except Exception as e:
        log_func(f"Ошибка выполнения скрипта: {e}", "error")
        return False
    finally:
        # Всегда сбрасываем флаг после завершения выполнения
        reset_stop_script_flag()

def send_stop_command(connection=None):
    """Останавливает выполнение скрипта на Arduino"""
    global log_func, arduino_connection, stop_script_flag
    
    # Устанавливаем флаг остановки
    set_stop_script_flag(True)
    
    conn = connection or arduino_connection
    if conn and conn.is_open:
        try:
            stop_command = "STOP\n"
            conn.write(stop_command.encode('utf-8'))
            conn.flush()
            log_func("Команда STOP отправлена на Arduino и флаг остановки установлен.", "info")
            return True
        except Exception as e:
            log_func(f"Ошибка отправки команды остановки: {e}", "error")
            return False
    else:
        log_func("Arduino не подключен, устанавливаю только флаг остановки.", "info")
        return True

def stop_script(connection=None):
    """Алиас для совместимости"""
    return send_stop_command(connection)

def save_scripts_settings(port_var_value, baud_rate_var_value, enabled_var, script_file_var_value, script_type_value, save_config_func, update_scripts_button_status_func):
    global log_func, global_context

    global_context['arduino_port'] = port_var_value
    global_context['arduino_baudrate'] = baud_rate_var_value
    global_context['scripts_enabled'] = (enabled_var.get() == 1)
    global_context['selected_script_file'] = script_file_var_value
    global_context['script_type'] = script_type_value

    try:
        save_config_func()
    except Exception as e:
        if log_func:
            log_func(f"Ошибка при сохранении конфига из arduino_controller: {e}", "error")

    try:
        update_scripts_button_status_func()
    except Exception as e:
        if log_func:
            log_func(f"Ошибка при обновлении статуса кнопки Скрипты: {e}", "error")

    if log_func:
        log_func(f"Настройки скриптов сохранены. Порт: {port_var_value}, Скорость: {baud_rate_var_value}, Файл: {script_file_var_value}, Тип: {script_type_value}, Включено: {global_context['scripts_enabled']}", "info")

def select_script_file():
    global script_file_var, log_func
    file_path = filedialog.askopenfilename(
        title="Выберите файл скрипта",
        filetypes=[
            ("Все файлы", "*.*"),  
            ("Текстовые файлы", "*.txt"),
            ("Python файлы", "*.py"),
            ("Arduino скрипты", "*.ino"),
        ]
    )
    if file_path:
        script_file_var.set(file_path)
        if log_func:
            log_message = f"Выбран файл скрипта: {os.path.basename(file_path)}"
            log_func(log_message, "info")
            # Автоматически определяем тип скрипта по расширению
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.py':
                log_message += " (Python скрипт)"
            elif ext == '.txt':
                log_message += " (текстовый скрипт)"
            elif ext == '.ino':
                log_message += " (Arduino скрипт)"
            log_func(log_message, "info")

def save_selected_script_action(port_var, baud_rate_var, enabled_var, script_file_var,
                               script_type_var, save_config_func, update_scripts_button_status_func):
    """Сохраняет выбранный скрипт и настройки"""
    global log_func, global_context
    
    # Получаем значения из переменных
    port_val = port_var.get()
    baud_val = baud_rate_var.get()
    script_file_val = script_file_var.get()
    script_type_val = script_type_var.get()
    enabled_val = enabled_var.get() == 1
    
    # Обновляем глобальный контекст
    global_context['arduino_port'] = port_val
    global_context['arduino_baudrate'] = baud_val
    global_context['selected_script_file'] = script_file_val
    global_context['script_type'] = script_type_val
    global_context['scripts_enabled'] = enabled_val
    global_context['arduino_connected'] = False  # Сбрасываем статус подключения
    
    try:
        # Вызываем функцию сохранения конфигурации из главного модуля
        save_config_func()
        if log_func:
            log_func(f"Скрипт и настройки сохранены. Файл: {os.path.basename(script_file_val) if script_file_val else 'не выбран'}", "info")
    except Exception as e:
        if log_func:
            log_func(f"Ошибка при сохранении конфига: {e}", "error")
    
    try:
        # Обновляем статус кнопки в главном окне
        update_scripts_button_status_func()
    except Exception as e:
        if log_func:
            log_func(f"Ошибка при обновлении статуса кнопки: {e}", "error")
    
    # Показываем сообщение об успешном сохранении
    if script_file_val:
        messagebox.showinfo("Сохранение", f"Скрипт сохранен:\n{os.path.basename(script_file_val)}\n\nПорт: {port_val}\nСкорость: {baud_val}\nТип: {script_type_val}")
    else:
        messagebox.showinfo("Сохранение", "Настройки сохранены (скрипт не выбран)")


# --- Основная функция GUI ---

def create_arduino_gui(parent_window, log_message_func, save_config_func, update_scripts_button_status_func, main_module_globals):
    global log_func, global_context, arduino_connection, connection_status_label, baud_rate_var, script_file_var, port_var
    log_func = log_message_func
    global_context = main_module_globals

    # Переключатель Включить/Отключить Скрипты
    enabled_var = tk.IntVar(value=1 if global_context.get('scripts_enabled') else 0)

    scripts_switch_frame = tk.LabelFrame(parent_window, text="Режим Скриптов", padx=10, pady=5)
    scripts_switch_frame.pack(pady=5, padx=10, fill=tk.X)

    def toggle_scripts():
        save_scripts_settings(
            port_var.get(),
            baud_rate_var.get(),
            enabled_var, 
            script_file_var.get(),
            script_type_var.get(),
            save_config_func, 
            update_scripts_button_status_func
        )
        if log_func:
            log_func(f"Режим скриптов переключен на {'ВКЛ' if enabled_var.get()==1 else 'ОТКЛ'} и сохранен.", "info")

    tk.Checkbutton(
        scripts_switch_frame,
        text="Включить Скрипты",
        variable=enabled_var,
        command=toggle_scripts
    ).pack(pady=5, anchor="w")

    # Фрейм для настроек Arduino
    arduino_frame = tk.LabelFrame(parent_window, text="Настройки Arduino", padx=10, pady=10)
    arduino_frame.pack(pady=5, padx=10, fill=tk.X)

    # 1. Выпадающий список COM-портов
    ports = list_serial_ports()
    port_var = tk.StringVar(parent_window)

    current_port = global_context.get('arduino_port', '')
    if current_port and current_port not in ports:
        ports.insert(0, current_port)
    if current_port:
        port_var.set(current_port)
    elif ports and ports[0]:
        port_var.set(ports[0])
    else:
        port_var.set('')

    tk.Label(arduino_frame, text="COM-порт:").grid(row=0, column=0, sticky="w", pady=5)
    port_dropdown = tk.OptionMenu(arduino_frame, port_var, *ports)
    port_dropdown.config(width=20)
    port_dropdown.grid(row=0, column=1, sticky="ew", pady=5, padx=5)

    # 2. Выпадающий список Скорости (Baud Rate)
    baud_rate_var = tk.StringVar(parent_window)
    current_baud = str(global_context.get('arduino_baudrate', BAUD_RATES[0]))
    if current_baud not in [str(r) for r in BAUD_RATES]:
        BAUD_RATES.insert(0, int(current_baud) if current_baud.isdigit() else BAUD_RATES[0])
    baud_rate_var.set(current_baud)

    tk.Label(arduino_frame, text="Скорость (Baud):").grid(row=1, column=0, sticky="w", pady=5)
    baud_dropdown = tk.OptionMenu(arduino_frame, baud_rate_var, *[str(r) for r in BAUD_RATES])
    baud_dropdown.config(width=20)
    baud_dropdown.grid(row=1, column=1, sticky="ew", pady=5, padx=5)

    # 3. Статус подключения
    connection_status_label = tk.Label(arduino_frame, text="Статус: Не подключено ❌", fg="red")
    connection_status_label.grid(row=2, column=0, columnspan=2, pady=5, sticky="w")
    
    update_connection_status()

    def connect_and_save_action():
        selected_port = port_var.get()
        selected_baud = baud_rate_var.get()
        
        global_context['arduino_port'] = selected_port
        global_context['arduino_baudrate'] = selected_baud
        global_context['scripts_enabled'] = (enabled_var.get() == 1)
        global_context['selected_script_file'] = script_file_var.get()
        global_context['script_type'] = script_type_var.get()
        
        try:
            save_config_func()
        except Exception as e:
            if log_func:
                log_func(f"Ошибка при сохранении конфига перед подключением: {e}", "error")

        success = arduino_connect(selected_port, selected_baud)
        
        if success:
            # Показать информационное сообщение о подключении
            messagebox.showinfo("Подключено", 
                              f"Успешно подключено к Arduino!\n"
                              f"Порт: {selected_port}\n"
                              f"Скорость: {selected_baud}\n\n")
        
        try:
            update_scripts_button_status_func()
        except Exception as e:
            if log_func:
                log_func(f"Ошибка при обновлении статуса кнопки Скрипты после подключения: {e}", "error")

    tk.Button(arduino_frame, text="Подключиться к Arduino", command=connect_and_save_action, width=25).grid(row=3, column=0, columnspan=2, pady=8)

    # Фрейм для управления скриптами
    scripts_frame = tk.LabelFrame(parent_window, text="Управление Скриптами", padx=10, pady=10)
    scripts_frame.pack(pady=15, padx=10, fill=tk.X)

    script_file_var = tk.StringVar(parent_window)
    script_file_var.set(global_context.get('selected_script_file', ''))

    # Тип скрипта
    script_type_var = tk.StringVar(parent_window)
    script_type_var.set(global_context.get('script_type', 'txt'))

    tk.Label(scripts_frame, text="Тип скрипта:").pack(pady=(0, 2), anchor="w")
    
    type_frame = tk.Frame(scripts_frame)
    type_frame.pack(fill=tk.X, pady=(0, 5))
    
    tk.Radiobutton(type_frame, text="Текстовый (.txt)", variable=script_type_var, value="txt").pack(side=tk.LEFT, padx=(0, 10))
    tk.Radiobutton(type_frame, text="Python (.py)", variable=script_type_var, value="py").pack(side=tk.LEFT)

    tk.Label(scripts_frame, text="Файл скрипта:").pack(pady=(0, 2), anchor="w")
    
    file_entry_frame = tk.Frame(scripts_frame)
    file_entry_frame.pack(fill=tk.X)

    tk.Entry(file_entry_frame, textvariable=script_file_var, state='readonly', width=30).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    tk.Button(file_entry_frame, text="Выбрать файл...", command=select_script_file).pack(side=tk.RIGHT)

    tk.Button(scripts_frame,
              text="Сохранить выбранный скрипт и настройки",
              command=lambda: save_selected_script_action(
                  port_var, 
                  baud_rate_var, 
                  enabled_var, 
                  script_file_var,
                  script_type_var,
                  save_config_func, 
                  update_scripts_button_status_func
              ),
              width=35).pack(pady=10)
