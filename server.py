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
            logger.debug(f'Receive the bus message: {message}')
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


async def send_to_browser(websocket):
    while True:
        message = {'msgType': 'Buses', 'buses': list(buses.values())}
        json_message = json.dumps(message, ensure_ascii=False)
        try:
            await websocket.send_message(json_message)
            logger.debug(f'Sent the message: {message}')
        except ConnectionClosed:
            break

        await trio.sleep(1)


async def listen_browser(websocket):
    while True:
        try:
            browser_message = await websocket.get_message()
            logger.debug(f'Received browser message: {browser_message}')
        except ConnectionClosed:
            break


async def talk_with_browser(request):
    ws = await request.accept()
    logger.debug(f'New browser connection has been established')
    async with trio.open_nursery() as nursery:
        sender = partial(send_to_browser, ws)
        listener = partial(listen_browser, ws)
        nursery.start_soon(sender)
        nursery.start_soon(listener)


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
            talk_with_browser,
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
