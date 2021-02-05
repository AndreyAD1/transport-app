from functools import partial
import json
import logging

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__file__)

# TODO Сделать глобальные переменные через каналы?
buses = {}
display_bounds = {}


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


def is_inside(bus):
    if not display_bounds:
        return True

    south_latitude = display_bounds['south_lat']
    north_latitude = display_bounds['north_lat']
    latitude_suits = south_latitude <= bus['lat'] <= north_latitude

    west_longitude = display_bounds['west_lng']
    east_longitude = display_bounds['east_lng']
    longitude_suits = west_longitude <= bus['lng'] <= east_longitude

    bus_is_inside_display = latitude_suits and longitude_suits
    return bus_is_inside_display


async def send_to_browser(websocket):
    while True:
        buses_on_screen = [bus for bus in buses.values() if is_inside(bus)]
        logger.debug(f'Displayed bus number {len(buses_on_screen)}')
        message = {'msgType': 'Buses', 'buses': buses_on_screen}
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

        warn_msg = 'Received the invalid browser message: {}'
        try:
            browser_msg_json = json.loads(browser_message)
        except json.JSONDecodeError:
            logger.warning(warn_msg.format(warn_msg))
            continue

        if browser_msg_json.get('msgType') == 'newBounds':
            new_display_boundaries = browser_msg_json.get('data')
            if new_display_boundaries:
                display_bounds.update(new_display_boundaries)
                logger.debug(f'Update display bounds: {display_bounds}')
            else:
                logger.warning(warn_msg.format(warn_msg))


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
