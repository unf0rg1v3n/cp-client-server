import asyncio
import json
import base64
from utils import SKID3, AESCipher

SHARED_SECRET = b"SecretKey123456789012345678901234" 

clients = {}  # id -> (writer, cipher, address)
_next_id = 1
clients_lock = asyncio.Lock()


async def broadcast(message: str, exclude_id: int | None = None):
    to_remove = []
    async with clients_lock:
        for cid, (writer, cipher, addr) in list(clients.items()):
            if cid == exclude_id:
                continue
            try:
                # Шифруем сообщение
                encrypted = cipher.encrypt(message)
                
                # Отправляем зашифрованное сообщение
                data = json.dumps({"encrypted": encrypted})
                writer.write((data + "\n").encode('utf-8'))
                await writer.drain()
            except Exception as e:
                print(f"Ошибка отправки клиенту {cid}: {e}")
                to_remove.append(cid)
        
        for cid in to_remove:
            w, _, _ = clients.pop(cid, (None, None, None))
            try:
                if w:
                    w.close()
                    await w.wait_closed()
            except Exception:
                pass


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global _next_id
    
    addr = writer.get_extra_info("peername")
    print(f"\n{'='*60}")
    print(f"Новое подключение от {addr}")
    print(f"{'='*60}")
    
    try:
        skid3 = SKID3(SHARED_SECRET)
        
        # Шаг 1: Получаем R_A от клиента (Alice)
        print(f"[{addr}] Ожидание R_A от клиента...")
        data = await reader.readline()
        if not data:
            print(f"[{addr}] Соединение закрыто до начала аутентификации")
            return
            
        msg = json.loads(data.decode('utf-8'))
        ra_b64 = msg.get("ra")
        if not ra_b64:
            print(f"[{addr}] Ошибка: не получен R_A")
            return
            
        ra = base64.b64decode(ra_b64)
        print(f"[{addr}] ✓ Получен R_A: {ra.hex()[:32]}...")
        
        # Шаг 2: Генерируем R_B и HMAC, отправляем клиенту
        print(f"[{addr}] Генерация R_B и вычисление HMAC...")
        rb, hmac_bob = skid3.respond_as_bob(ra)
        
        response = {
            "rb": base64.b64encode(rb).decode('utf-8'),
            "hmac": base64.b64encode(hmac_bob).decode('utf-8')
        }
        writer.write((json.dumps(response) + "\n").encode('utf-8'))
        await writer.drain()
        print(f"[{addr}] ✓ Отправлены R_B и HMAC")
        print(f"[{addr}]   R_B: {rb.hex()[:32]}...")
        print(f"[{addr}]   HMAC: {hmac_bob.hex()[:32]}...")
        
        # Шаг 3: Получаем и проверяем HMAC от клиента
        print(f"[{addr}] Ожидание HMAC от клиента...")
        data = await reader.readline()
        if not data:
            print(f"[{addr}] Соединение закрыто до завершения аутентификации")
            return
            
        msg = json.loads(data.decode('utf-8'))
        hmac_alice_b64 = msg.get("hmac")
        if not hmac_alice_b64:
            print(f"[{addr}] Ошибка: не получен HMAC от клиента")
            return
            
        hmac_alice = base64.b64decode(hmac_alice_b64)
        print(f"[{addr}] ✓ Получен HMAC: {hmac_alice.hex()[:32]}...")
        
        # Проверяем HMAC
        print(f"[{addr}] Проверка аутентификации...")
        skid3.verify_as_bob(hmac_alice)
        print(f"[{addr}] ✓✓✓ АУТЕНТИФИКАЦИЯ УСПЕШНА! ✓✓✓")
        
        # Получаем сессионный ключ
        session_key = skid3.get_session_key()
        print(f"[{addr}] Сессионный ключ установлен: {session_key.hex()[:32]}...")
        print(f"{'='*60}\n")
        
        # Создаем AES шифр для сессии
        cipher = AESCipher(session_key)
        
        # Регистрируем клиента
        async with clients_lock:
            cid = _next_id
            _next_id += 1
            clients[cid] = (writer, cipher, addr)
        
        print(f"✓ Клиент {cid} успешно подключен: {addr}")
        
        # Отправляем подтверждение успешной аутентификации
        success_msg = json.dumps({"status": "authenticated", "client_id": cid})
        writer.write((success_msg + "\n").encode('utf-8'))
        await writer.drain()
        
        # Уведомляем других клиентов
        await broadcast(f"[Сервер] Клиент {cid} подключился", exclude_id=cid)

        while True:
            data = await reader.readline()
            if not data:
                break
                
            try:
                msg = json.loads(data.decode('utf-8').strip())
                encrypted = msg.get("encrypted")
                
                if not encrypted:
                    continue
                
                # Дешифруем сообщение
                text = cipher.decrypt(encrypted)
                
                print(f"[Клиент {cid}]: {text}")
                
                # Рассылаем всем остальным
                await broadcast(f"[Клиент {cid}]: {text}", exclude_id=cid)
                
            except Exception as e:
                print(f"Ошибка обработки сообщения от клиента {cid}: {e}")
                continue
                
    except ValueError as e:
        # Ошибка аутентификации
        print(f"[{addr}] ✗✗✗ ОШИБКА АУТЕНТИФИКАЦИИ: {e}")
        try:
            error_msg = json.dumps({"status": "auth_failed", "error": str(e)})
            writer.write((error_msg + "\n").encode('utf-8'))
            await writer.drain()
        except:
            pass
            
    except asyncio.CancelledError:
        pass
        
    except Exception as e:
        print(f"Ошибка с клиентом {addr}: {e}")
        
    finally:
        # Удаляем клиента
        if 'cid' in locals():
            async with clients_lock:
                clients.pop(cid, None)
            await broadcast(f"[Сервер] Клиент {cid} отключился", exclude_id=cid)
            print(f"✗ Клиент {cid} отключен: {addr}")
        
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8888)
    addr = server.sockets[0].getsockname()
    
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "СЕРВЕР ЗАЩИЩЕННОГО ЧАТА (SKID3)" + " " * 16 + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  Адрес: {addr[0]:15s}                                  ║")
    print(f"║  Порт:  {addr[1]:15d}                                  ║")
    print(f"║  Протокол: SKID3 + AES-256-CBC                       ║")
    print(f"║  Хэш-функция: HMAC-SHA256                            ║")
    print("╚" + "═" * 58 + "╝")
    print()

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nСервер остановлен пользователем")