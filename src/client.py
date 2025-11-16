import asyncio
import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import base64
from utils import SKID3, AESCipher
import threading

SHARED_SECRET = b"SecretKey123456789012345678901234"


class ChatClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Защищенный чат - Протокол SKID3")
        self.geometry("700x500")
        self.configure(bg='#2C3E50')
        
        # Переменные протокола
        self.skid3 = SKID3(SHARED_SECRET)
        self.cipher = None
        self.authenticated = False
        self.client_id = None
        
        # Создание GUI
        self.create_widgets()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True

        # Создаем отдельный поток для asyncio
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

    def create_widgets(self):
        """Создает элементы графического интерфейса"""
        
        # Заголовок
        header_frame = tk.Frame(self, bg='#34495E', height=60)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="🔒 Защищенный чат с протоколом SKID3",
            font=('Arial', 14, 'bold'),
            bg='#34495E',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # Статус подключения
        self.status_frame = tk.Frame(self, bg='#95A5A6', height=30)
        self.status_frame.pack(fill=tk.X, padx=0, pady=0)
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            self.status_frame,
            text="⚠ Подключение...",
            font=('Arial', 9),
            bg='#95A5A6',
            fg='#2C3E50'
        )
        self.status_label.pack(pady=5)
        
        # Область чата
        chat_frame = tk.Frame(self, bg='#2C3E50')
        chat_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#ECF0F1',
            fg='#2C3E50',
            insertbackground='#2C3E50'
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.config(state=tk.DISABLED)
        
        # Область ввода
        self.input_frame = tk.Frame(self, bg='#2C3E50')
        self.input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        self.message_entry = tk.Entry(
            self.input_frame,
            font=('Arial', 11),
            bg='#ECF0F1',
            fg='#2C3E50',
            insertbackground='#2C3E50'
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        self.message_entry.config(state=tk.DISABLED)
        
        self.send_button = tk.Button(
            self.input_frame,
            text="Отправить",
            command=self.send_message,
            font=('Arial', 10, 'bold'),
            bg='#3498DB',
            fg='white',
            activebackground='#2980B9',
            activeforeground='white',
            padx=20,
            state=tk.DISABLED
        )
        self.send_button.pack(side=tk.RIGHT, padx=(5, 0))

    def run_async_loop(self):
        """Запускает event loop в отдельном потоке"""
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.main())
        self.loop.run_forever()

    def append_message(self, message, msg_type='normal'):
        """Добавляет сообщение в область чата"""
        self.after(0, lambda: self._append_message(message, msg_type))

    def _append_message(self, message, msg_type):
        """Внутренний метод для добавления сообщения"""
        self.chat_area.config(state=tk.NORMAL)
        
        if msg_type == 'system':
            self.chat_area.insert(tk.END, ">>> ", 'system')
            self.chat_area.insert(tk.END, message + "\n", 'system')
        elif msg_type == 'error':
            self.chat_area.insert(tk.END, "⚠ ", 'error')
            self.chat_area.insert(tk.END, message + "\n", 'error')
        elif msg_type == 'success':
            self.chat_area.insert(tk.END, "✓ ", 'success')
            self.chat_area.insert(tk.END, message + "\n", 'success')
        else:
            self.chat_area.insert(tk.END, message + "\n")
        
        # Настройка тегов
        self.chat_area.tag_config('system', foreground='#7F8C8D', font=('Consolas', 9, 'italic'))
        self.chat_area.tag_config('error', foreground='#E74C3C', font=('Consolas', 10, 'bold'))
        self.chat_area.tag_config('success', foreground='#27AE60', font=('Consolas', 10, 'bold'))
        
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def update_status(self, text, color='#95A5A6'):
        """Обновляет статус подключения"""
        self.after(0, lambda: self._update_status(text, color))

    def _update_status(self, text, color):
        """Внутренний метод для обновления статуса"""
        self.status_label.config(text=text)
        self.status_frame.config(bg=color)
        self.status_label.config(bg=color)

    def enable_chat(self):
        """Включает возможность отправки сообщений"""
        self.after(0, self._enable_chat)

    def _enable_chat(self):
        """Внутренний метод для включения чата"""
        self.message_entry.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.message_entry.focus()
        
    def send_message(self):
        """Отправляет сообщение"""
        message = self.message_entry.get()
        if message and self.authenticated and hasattr(self, 'writer') and self.writer:
            try:
                # Шифруем сообщение
                encrypted = self.cipher.encrypt(message)
                
                # Отправляем зашифрованное сообщение
                data = json.dumps({"encrypted": encrypted})
                asyncio.run_coroutine_threadsafe(
                    self._send_message(data), 
                    self.loop
                )
                
                self.message_entry.delete(0, tk.END)
                self.append_message(f"Вы: {message}")
                
            except Exception as e:
                self.append_message(f"Ошибка отправки: {e}", 'error')

    async def _send_message(self, data):
        """Асинхронная отправка сообщения"""
        self.writer.write((data + "\n").encode('utf-8'))
        await self.writer.drain()
            
    def on_closing(self):
        """Обработка закрытия окна"""
        self.running = False
        if hasattr(self, 'writer') and self.writer:
            self.loop.call_soon_threadsafe(self.writer.close)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.destroy()
        
    async def main(self):
        """Главная функция клиента"""
        try:
            self.append_message("Подключение к серверу...", 'system')
            self.reader, self.writer = await asyncio.open_connection("127.0.0.1", 8888)
            self.append_message("Соединение установлено", 'success')
            
            # ===== ПРОТОКОЛ SKID3 - АУТЕНТИФИКАЦИЯ =====
            self.append_message("", 'system')
            self.append_message("=== Начало протокола SKID3 ===", 'system')
            
            # Шаг 1: Инициируем как Alice - генерируем и отправляем R_A
            self.append_message("Генерация случайного числа R_A...", 'system')
            ra = self.skid3.initiate_as_alice()
            
            msg = {"ra": base64.b64encode(ra).decode('utf-8')}
            self.writer.write((json.dumps(msg) + "\n").encode('utf-8'))
            await self.writer.drain()
            self.append_message("✓ R_A отправлен серверу", 'success')
            
            # Шаг 2: Получаем R_B и HMAC от сервера
            self.append_message("Ожидание ответа от сервера...", 'system')
            data = await self.reader.readline()
            if not data:
                raise ConnectionError("Сервер закрыл соединение")
                
            response = json.loads(data.decode('utf-8'))
            rb = base64.b64decode(response["rb"])
            hmac_bob = base64.b64decode(response["hmac"])
            self.append_message("✓ Получены R_B и HMAC от сервера", 'success')
            
            # Шаг 3: Проверяем HMAC и отправляем свой
            self.append_message("Проверка подлинности сервера...", 'system')
            hmac_alice = self.skid3.verify_and_respond_as_alice(rb, hmac_bob)
            self.append_message("✓ Сервер аутентифицирован!", 'success')
            
            msg = {"hmac": base64.b64encode(hmac_alice).decode('utf-8')}
            self.writer.write((json.dumps(msg) + "\n").encode('utf-8'))
            await self.writer.drain()
            self.append_message("✓ HMAC отправлен серверу", 'success')
            
            # Получаем сессионный ключ
            session_key = self.skid3.get_session_key()
            self.cipher = AESCipher(session_key)
            
            # Ждем подтверждения от сервера
            data = await self.reader.readline()
            if not data:
                raise ConnectionError("Сервер закрыл соединение")
                
            response = json.loads(data.decode('utf-8'))
            if response.get("status") == "authenticated":
                self.client_id = response.get("client_id")
                self.authenticated = True
                
                self.append_message("", 'system')
                self.append_message("✓✓✓ АУТЕНТИФИКАЦИЯ УСПЕШНА! ✓✓✓", 'success')
                self.append_message(f"Ваш ID: {self.client_id}", 'success')
                self.append_message("Сессионный ключ установлен", 'success')
                self.append_message("=== Протокол SKID3 завершен ===", 'system')
                self.append_message("", 'system')
                
                self.update_status(f"✓ Подключено (ID: {self.client_id}) - Защищено SKID3", '#27AE60')
                self.enable_chat()
                
            elif response.get("status") == "auth_failed":
                raise ValueError(f"Аутентификация не удалась: {response.get('error')}")
            
            # ===== ОСНОВНОЙ ЦИКЛ ПОЛУЧЕНИЯ СООБЩЕНИЙ =====
            while self.running and self.authenticated:
                data = await self.reader.readline()
                if not data:
                    break
                    
                try:
                    msg = json.loads(data.decode('utf-8'))
                    encrypted = msg.get("encrypted")
                    
                    if encrypted:
                        # Дешифруем сообщение
                        text = self.cipher.decrypt(encrypted)
                        self.append_message(text)
                        
                except Exception as e:
                    self.append_message(f"Ошибка дешифрования: {e}", 'error')
                    continue
                    
        except ValueError as e:
            self.append_message(f"ОШИБКА АУТЕНТИФИКАЦИИ: {e}", 'error')
            self.update_status("✗ Ошибка аутентификации", '#E74C3C')
            messagebox.showerror("Ошибка", f"Аутентификация не удалась:\n{e}")
            
        except ConnectionError as e:
            self.append_message(f"Ошибка соединения: {e}", 'error')
            self.update_status("✗ Соединение потеряно", '#E74C3C')
            
        except Exception as e:
            self.append_message(f"Ошибка: {e}", 'error')
            self.update_status("✗ Ошибка", '#E74C3C')
            
        finally:
            if hasattr(self, 'writer'):
                try:
                    self.writer.close()
                    await self.writer.wait_closed()
                except:
                    pass


if __name__ == "__main__":
    client = ChatClient()
    client.mainloop()