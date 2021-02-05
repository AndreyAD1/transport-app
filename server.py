from dataclasses import dataclass, asdict
from functools import partial
import json
import logging

import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__file__)

# TODO Сделать глобальные переменные через каналы?
buses = {}


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str


class PrintClassWithAttrs(type):
    def __str__(self):
        attrs = {n: v for n, v in vars(self).items() if not n.startswith('__')}
        return f'{self.__name__}: {attrs}'


class WindowBounds(metaclass=PrintClassWithAttrs):
    south_latitude = None
    north_latitude = None
    west_longitude = None
    east_longitude = None

    @classmethod
    def is_inside(cls, bus: Bus):
        if not all(
                [
                    cls.south_latitude,
                    cls.north_latitude,
                    cls.west_longitude,
                    cls.east_longitude
                ]
        ):
            return False

        latitude_suits = cls.south_latitude <= bus.lat <= cls.north_latitude
        longitude_suits = cls.west_longitude <= bus.lng <= cls.east_longitude
        bus_is_inside_window = latitude_suits and longitude_suits
        return bus_is_inside_window


async def handle_bus_coordinates(request):
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

        buses[bus_id] = Bus(
            bus_info.get('busId'),
            bus_info.get('lat'),
            bus_info.get('lng'),
            bus_info.get('route')
        )


async def send_to_browser(websocket):
    while True:
        buses_on_screen = [
            asdict(bus) for bus in buses.values() if WindowBounds.is_inside(bus)
        ]
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
            new_window_bounds = browser_msg_json.get('data')
            if new_window_bounds:
                WindowBounds.south_latitude = new_window_bounds['south_lat']
                WindowBounds.north_latitude = new_window_bounds['north_lat']
                WindowBounds.west_longitude = new_window_bounds['west_lng']
                WindowBounds.east_longitude = new_window_bounds['east_lng']
                logger.debug(f'Update display bounds: {WindowBounds}')
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
            handle_bus_coordinates,
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
