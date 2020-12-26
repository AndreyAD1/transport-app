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
            logger.debug(f'Received the bus message: {message}')
        except ConnectionClosed:
            logger.debug(f'Connection closed')
            break

        try:
            bus_info = json.loads(message)
        except json.JSONDecodeError:
            logger.error('Can not parse received message to JSON')
            # TODO return an error to the client
            continue

        bus_id = bus_info.get('busId')
        if bus_id is None:
            logger.error('No key "busId" is in the received JSON')
            # TODO return an error to the client
            continue

        buses[bus_id] = bus_info


async def talk_to_browser(request):
    ws = await request.accept()
    logger.debug(f'New browser connection has been established')
    browser_message = await ws.get_message()
    logger.debug(f'Received the browser message: {browser_message}')
    while True:
        try:
            response = {'msgType': 'Buses', 'buses': list(buses.values())}
            await ws.send_message(json.dumps(response, ensure_ascii=False))
            logger.debug(f'Send the message: {response}')
        except ConnectionClosed:
            break
        await trio.sleep(1)


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
