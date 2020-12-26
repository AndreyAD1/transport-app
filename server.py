import logging

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__file__)


async def handle_coordinates(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            logger.debug(f'Received bus info: {message}')
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    logger.setLevel(logging.DEBUG)
    trio.run(main)
