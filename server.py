from functools import partial
import json
import logging

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__file__)

buses = {}


async def handle_coordinates(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            logger.debug(f'Received bus info: {message}')
        except ConnectionClosed:
            break


async def talk_to_browser(request):
    ws = await request.accept()
    logger.debug(f'New browser connection has been established')
    while True:
        try:
            browser_message = await ws.get_message()
            logger.debug(f'New browser message: {browser_message}')
            response = {'msgType': 'Buses', 'buses': buses}
            await ws.send_message(json.dumps(response, ensure_ascii=False))
        except ConnectionClosed:
            break


async def main():
    async with trio.open_nursery() as nursery:
        coordinate_handler = partial(
            serve_websocket,
            handle_coordinates,
            '127.0.0.1',
            8080,
            None
        )
        browser_talker = partial(
            serve_websocket,
            talk_to_browser,
            '127.0.0.1',
            8000,
            None
        )
        nursery.start_soon(coordinate_handler)
        nursery.start_soon(browser_talker)


if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    logger.setLevel(logging.DEBUG)
    trio.run(main)
