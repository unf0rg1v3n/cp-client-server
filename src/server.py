import asyncio
import json
from utils import RSA

clients = {}  # id -> (writer, public_key)
_next_id = 1
clients_lock = asyncio.Lock()
rsa = RSA()

async def broadcast(message: str, exclude_id: int | None = None):
    to_remove = []
    async with clients_lock:
        for cid, (writer, pub_key) in list(clients.items()):
            if cid == exclude_id:
                continue
            try:
                # Шифруем сообщение блоками
                encrypted_blocks = RSA.encrypt_message(message, pub_key[0], pub_key[1])
                # Отправляем зашифрованные блоки как JSON
                writer.write((json.dumps(encrypted_blocks) + "\n").encode('utf-8'))
                await writer.drain()
            except Exception as e:
                print(f"Ошибка отправки клиенту {cid}: {e}")
                to_remove.append(cid)
        
        for cid in to_remove:
            w, _ = clients.pop(cid, (None, None))
            try:
                if w:
                    w.close()
                    await w.wait_closed()
            except Exception:
                pass

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global _next_id
    
    # Получаем публичный ключ клиента
    data = await reader.readline()
    client_key = json.loads(data.decode())
    client_public_key = (client_key["e"], client_key["n"])
    
    # Отправляем наш публичный ключ
    writer.write((json.dumps({"e": rsa.e, "n": rsa.n}) + "\n").encode())
    await writer.drain()
    
    async with clients_lock:
        cid = _next_id
        _next_id += 1
        clients[cid] = (writer, client_public_key)

    addr = writer.get_extra_info("peername")
    print(f"Клиент {cid} подключился: {addr}")
    await broadcast(f"[Server] Клиент {cid} подключился", exclude_id=cid)

    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            try:
                # Получаем список зашифрованных блоков
                encrypted_blocks = json.loads(data.decode('utf-8').strip())
                # Дешифруем сообщение из блоков
                text = rsa.decrypt_message(encrypted_blocks)
                
                print(f"[Клиент {cid}]: {text}")
                await broadcast(f"[Клиент {cid}]: {text}", exclude_id=cid)
            except Exception as e:
                print(f"Ошибка обработки сообщения от клиента {cid}: {e}")
                continue
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Ошибка с клиентом {cid}: {e}")
    finally:
        async with clients_lock:
            clients.pop(cid, None)
        await broadcast(f"[Server] Клиент {cid} отключился", exclude_id=cid)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8888)
    addr = server.sockets[0].getsockname()
    print(f"Сервер запущен на {addr}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())