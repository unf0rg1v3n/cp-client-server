import asyncio

async def read_from_server(reader):
    while True:
        data = await reader.read(100)
        if not data:
            print("Сервер закрыл соединение")
            break
        print(f"[Сервер]: {data.decode()}")

async def write_to_server(writer):
    while True:
        # вызываем input в отдельном потоке, чтобы не блокировать event loop
        msg = await asyncio.to_thread(input, "Введите сообщение: ")
        if msg.lower() == "exit":
            break
        writer.write(msg.encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()

async def main():
    reader, writer = await asyncio.open_connection("127.0.0.1", 8888)

    # параллельно запускаем чтение и запись
    task_read = asyncio.create_task(read_from_server(reader))
    task_write = asyncio.create_task(write_to_server(writer))

    await asyncio.gather(task_read, task_write)

asyncio.run(main())
