import asyncio

async def read_from_client(reader):
    while True:
        data = await reader.read(100)
        if not data:
            print("Клиент отключился")
            break
        print(f"[Клиент]: {data.decode()}")

async def write_to_client(writer):
    while True:
        msg = await asyncio.to_thread(input, "Введите сообщение клиенту: ")
        if msg.lower() == "exit":
            break
        writer.write(msg.encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()

async def handle_client(reader, writer):
    task_read = asyncio.create_task(read_from_client(reader))
    task_write = asyncio.create_task(write_to_client(writer))

    await asyncio.gather(task_read, task_write)

async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 8888)
    addr = server.sockets[0].getsockname()
    print(f"Сервер запущен на {addr}")

    async with server:
        await server.serve_forever()

asyncio.run(main())
