"""
Script API for Arduino controller
Provides safe execution environment for Python scripts
"""
import time
import threading
import traceback
import math
import random
import datetime
import os


class ScriptAPI:
    """Безопасный API для выполнения скриптов с доступом к Arduino."""
    
    def __init__(self, 
                 arduino_connection,
                 log_func,
                 get_stop_flag,
                 set_stop_flag):
        """
        Инициализация API.
        
        Args:
            arduino_connection: Соединение с Arduino
            log_func: Функция для логирования
            get_stop_flag: Функция получения флага остановки
            set_stop_flag: Функция установки флага остановки
        """
        self.arduino = arduino_connection
        self.log = log_func
        self._get_stop_flag = get_stop_flag
        self._set_stop_flag = set_stop_flag
        self._script_vars = {}
        self._execution_thread = None
        self._force_stop_event = threading.Event()  # Событие для принудительной остановки
        self._stop_requested = False  # Флаг запроса остановки
        
    def force_stop(self):
        """Принудительная остановка скрипта."""
        self._stop_requested = True
        self._force_stop_event.set()
        self._set_stop_flag(True)
        self.log("Принудительная остановка скрипта запрошена", "warning")
        
    def send(self, command):
        """Отправляет команду на Arduino с проверкой остановки."""
        if self._get_stop_flag() or self._stop_requested:
            return False
            
        if not self.arduino or not hasattr(self.arduino, 'is_open') or not self.arduino.is_open:
            self.log("Arduino не подключен", "warning")
            return False
            
        try:
            command_bytes = f"{command}\n".encode('utf-8')
            self.arduino.write(command_bytes)
            self.arduino.flush()
            return True
        except Exception as e:
            self.log(f"Ошибка отправки команды '{command}': {e}", "error")
            return False
    
    def wait(self, seconds):
        """
        Ждет указанное время с проверкой флага остановки.
        Возвращает False если скрипт остановлен.
        """
        if seconds <= 0:
            return True
            
        # Используем событие для возможности прерывания
        if self._force_stop_event.wait(timeout=seconds):
            return False  # Была принудительная остановка
            
        # Проверяем другие флаги остановки
        return not (self._get_stop_flag() or self._stop_requested)
    
    def sleep(self, seconds):
        """Алиас для wait."""
        return self.wait(seconds)
    
    def log_message(self, message, level="info"):
        """Записывает сообщение в лог."""
        self.log(message, level)
    
    def print(self, message):
        """Выводит сообщение (аналог print для скриптов)."""
        self.log(f"[Скрипт] {message}", "info")
    
    def set_var(self, name, value):
        """Устанавливает переменную, доступную в скрипте."""
        self._script_vars[name] = value
    
    def get_var(self, name, default=None):
        """Получает значение переменной скрипта."""
        return self._script_vars.get(name, default)
    
    def is_stopped(self):
        """Проверяет, установлен ли флаг остановки."""
        return self._get_stop_flag() or self._stop_requested
    
    def stop_script(self):
        """Останавливает выполнение текущего скрипта."""
        self._set_stop_flag(True)
        self._stop_requested = True
        self._force_stop_event.set()
        self.log("Скрипт запросил остановку", "info")
    
    def get_info(self):
        """Возвращает информацию о скриптовой среде."""
        return {
            "arduino_connected": self.arduino and hasattr(self.arduino, 'is_open') and self.arduino.is_open,
            "script_stopped": self._get_stop_flag() or self._stop_requested,
            "script_vars_count": len(self._script_vars),
            "stop_requested": self._stop_requested
        }
    
    def execute_python_script(self, script_path):
        """Выполняет Python-скрипт."""
        if not os.path.exists(script_path):
            self.log(f"Файл скрипта не найден: {script_path}", "error")
            return False
        
        # Сбрасываем флаги перед запуском
        self._stop_requested = False
        self._force_stop_event.clear()
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_code = f.read()
            
            # Создаем безопасное окружение
            safe_globals = self._create_safe_environment(script_path)
            
            # Запускаем в отдельном потоке
            self._execution_thread = threading.Thread(
                target=self._execute_in_thread,
                args=(script_code, safe_globals),
                name=f"ScriptThread-{os.path.basename(script_path)}"
            )
            self._execution_thread.daemon = True  # Поток-демон завершится при завершении основной программы
            self._execution_thread.start()
            
            # Ждем завершения
            self._execution_thread.join(timeout=300)  # 5 минут макс
            
            if self._execution_thread.is_alive():
                self.log("Скрипт превысил лимит времени выполнения", "warning")
                # Пытаемся принудительно остановить
                self.force_stop()
                return False
                
            return True
            
        except Exception as e:
            self.log(f"Ошибка выполнения Python-скрипта: {e}", "error")
            return False
        finally:
            # Очищаем ссылку на поток
            self._execution_thread = None
    
    def _create_safe_environment(self, script_path):
        """Создает безопасное окружение для выполнения скрипта."""
        safe_globals = {
            '__name__': '__main__',
            '__file__': script_path,
            'arduino': self,
            'api': self,
            
            # Основные функции
            'print': self.print,
            'sleep': self.sleep,
            'wait': self.wait,
            'log': self.log_message,
            'is_stopped': self.is_stopped,
            'stop_script': self.stop_script,
            'set_var': self.set_var,
            'get_var': self.get_var,
            'get_info': self.get_info,
            
            # Безопасные модули
            'math': math,
            'random': random,
            'datetime': datetime,
            'time': time,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'range': range,
            'len': len,
            
            # Дополнительные полезные функции
            'exit': self.stop_script,
            'quit': self.stop_script,
        }
        
        return safe_globals
    
    def _execute_in_thread(self, script_code, safe_globals):
        """Выполняет скрипт в потоке."""
        try:
            # Компилируем код
            compiled_code = compile(script_code, safe_globals['__file__'], 'exec')
            
            # Выполняем
            exec(compiled_code, safe_globals)
            
            if not (self._get_stop_flag() or self._stop_requested):
                self.log("Python-скрипт успешно завершен", "info")
                
        except KeyboardInterrupt:
            self.log("Скрипт прерван пользователем", "info")
            self.stop_script()
        except SystemExit:
            self.log("Скрипт завершился с SystemExit", "info")
            self.stop_script()
        except Exception as e:
            self.log(f"Ошибка в скрипте: {traceback.format_exc()}", "error")
            self.stop_script()


def execute_python_script_wrapper(script_path, arduino_conn, log_func, get_stop_flag, set_stop_flag):
    """Обертка для выполнения Python-скрипта."""
    try:
        api = ScriptAPI(arduino_conn, log_func, get_stop_flag, set_stop_flag)
        return api.execute_python_script(script_path)
    except Exception as e:
        log_func(f"Ошибка создания API: {e}", "error")
        return False


def force_stop_script(api_instance):
    """Принудительно останавливает выполнение скрипта."""
    if api_instance:
        api_instance.force_stop()
        return True
    return False


# Глобальный флаг доступности API
SCRIPT_API_AVAILABLE = True
