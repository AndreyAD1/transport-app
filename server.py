import trio
from trio_websocket import serve_websocket, ConnectionClosed


async def handle_coordinates(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            print(message)
        except ConnectionClosed:
            break
        await trio.sleep(1)


async def main():
    await serve_websocket(
        handle_coordinates,
        '127.0.0.1',
        8080,
        ssl_context=None
    )


trio.run(main)