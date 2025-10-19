import asyncio
import tkinter as tk
from tkinter import scrolledtext
import json
from utils import RSA
import threading

class ChatClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Защищенный чат")
        self.geometry("600x400")
        
        self.rsa = RSA()
        self.server_public_key = None
        
        # GUI elements
        self.chat_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=20)
        self.chat_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.input_frame = tk.Frame(self)
        self.input_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.message_entry = tk.Entry(self.input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.send_button = tk.Button(self.input_frame, text="Отправить", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=5)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True

        # Create new thread for asyncio event loop
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.main())
        self.loop.run_forever()

    def append_message(self, message):
        self.after(0, lambda: self._append_message(message))

    def _append_message(self, message):
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.see(tk.END)
        
    def send_message(self):
        message = self.message_entry.get()
        if message and hasattr(self, 'writer') and self.writer:
            try:
                # Шифруем сообщение блоками
                encrypted_blocks = RSA.encrypt_message(message, self.server_public_key[0], self.server_public_key[1])
                # Отправляем зашифрованные блоки как JSON
                encrypted_json = json.dumps(encrypted_blocks)
                asyncio.run_coroutine_threadsafe(self._send_message(encrypted_json), self.loop)
                self.message_entry.delete(0, tk.END)
                self.append_message(f"Вы: {message}")
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")

    async def _send_message(self, encrypted_json):
        self.writer.write((encrypted_json + "\n").encode())
        await self.writer.drain()
            
    def on_closing(self):
        self.running = False
        if hasattr(self, 'writer') and self.writer:
            self.loop.call_soon_threadsafe(self.writer.close)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.destroy()
        
    async def main(self):
        try:
            self.reader, self.writer = await asyncio.open_connection("127.0.0.1", 8888)
            
            # Отправляем наш публичный ключ
            pub_key = json.dumps({"e": self.rsa.e, "n": self.rsa.n})
            self.writer.write((pub_key + "\n").encode())
            await self.writer.drain()
            
            # Получаем публичный ключ сервера
            data = await self.reader.readline()
            server_key = json.loads(data.decode())
            self.server_public_key = (server_key["e"], server_key["n"])
            
            while self.running:
                data = await self.reader.readline()
                if not data:
                    break
                try:
                    # Получаем список зашифрованных блоков
                    encrypted_blocks = json.loads(data.decode('utf-8'))
                    # Дешифруем сообщение из блоков
                    message = self.rsa.decrypt_message(encrypted_blocks)
                    self.append_message(message)
                except Exception as e:
                    print(f"Ошибка расшифровки: {e}")
                    continue
                    
        except Exception as e:
            print(f"Ошибка соединения: {e}")
        finally:
            if hasattr(self, 'writer'):
                self.writer.close()
                await self.writer.wait_closed()

if __name__ == "__main__":
    client = ChatClient()
    client.mainloop()