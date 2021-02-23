from dataclasses import dataclass, asdict
from functools import partial
import json
import logging

import click
import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__file__)

COORDINATE_NAMES = ['south_lat', 'north_lat', 'west_lng', 'east_lng']
# TODO Сделать глобальные переменные через каналы?
buses = {}


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str


@dataclass
class WindowBounds:
    def __init__(self):
        self.south_latitude = None
        self.north_latitude = None
        self.west_longitude = None
        self.east_longitude = None

    def __str__(self):
        attrs = {n: v for n, v in vars(self).items() if not n.startswith('__')}
        return f'WindowBounds: {attrs}'

    def is_inside(self, bus: Bus):
        window_coords = [
            self.south_latitude,
            self.north_latitude,
            self.west_longitude,
            self.east_longitude
        ]
        if not all(window_coords):
            logger.warning(f'Invalid window coordinates: {self}')
            return False

        latitude_suits = self.south_latitude <= bus.lat <= self.north_latitude
        longitude_suits = self.west_longitude <= bus.lng <= self.east_longitude
        bus_is_inside_window = latitude_suits and longitude_suits
        return bus_is_inside_window

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_latitude = south_lat
        self.north_latitude = north_lat
        self.west_longitude = west_lng
        self.east_longitude = east_lng


async def handle_bus_coordinates(request):
    websocket = await request.accept()
    while True:
        try:
            message = await websocket.get_message()
            logger.debug(f'Receive the bus message: {message}')
        except ConnectionClosed:
            logger.debug(f'Connection closed')
            break

        try:
            bus_info = json.loads(message)
        except json.JSONDecodeError:
            logger.error(
                'Invalid request.  Can not unmarshal received message to JSON'
            )
            error_msg = {
                'errors': ['Requires valid JSON'],
                'msgType': 'Errors'
            }
            error_json = json.dumps(error_msg)
            await websocket.send_message(error_json)
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


async def send_to_browser(websocket, window_bounds: WindowBounds):
    while True:
        buses_on_screen = [
            asdict(b) for b in buses.values() if window_bounds.is_inside(b)
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


async def listen_browser(websocket, window_bounds: WindowBounds):
    while True:
        try:
            browser_message = await websocket.get_message()
            logger.debug(f'Received browser message: {browser_message}')
        except ConnectionClosed:
            break

        warn_msg = 'The invalid browser message received: {}'
        try:
            browser_msg_json = json.loads(browser_message)
        except json.JSONDecodeError:
            logger.warning(warn_msg.format(warn_msg))
            # TODO Return an error
            continue

        if browser_msg_json.get('msgType') == 'newBounds':
            new_window_bounds = browser_msg_json.get('data')
            if new_window_bounds:
                new_window_coords = [
                    new_window_bounds.get(name) for name in COORDINATE_NAMES
                ]
                if all(new_window_coords):
                    window_bounds.update(
                        new_window_bounds.get('south_lat'),
                        new_window_bounds.get('north_lat'),
                        new_window_bounds.get('west_lng'),
                        new_window_bounds.get('east_lng')
                    )
                    logger.debug(f'Update display bounds: {window_bounds}')
                else:
                    logger.warning(warn_msg.format(warn_msg))
            else:
                logger.warning(warn_msg.format(warn_msg))


async def talk_with_browser(request):
    ws = await request.accept()
    logger.debug(f'New browser connection has been established')
    async with trio.open_nursery() as nursery:
        window_bounds = WindowBounds()
        sender = partial(send_to_browser, ws, window_bounds)
        listener = partial(listen_browser, ws, window_bounds)
        nursery.start_soon(sender)
        nursery.start_soon(listener)


async def start_server(bus_port, browser_port):
    async with trio.open_nursery() as nursery:
        coordinate_handler = partial(
            serve_websocket,
            handle_bus_coordinates,
            '127.0.0.1',
            bus_port,
            None
        )
        browser_talker = partial(
            serve_websocket,
            talk_with_browser,
            '127.0.0.1',
            browser_port,
            None
        )
        nursery.start_soon(coordinate_handler)
        nursery.start_soon(browser_talker)


@click.command()
@click.option(
    '--bus_port',
    type=int,
    help='A number of port for bus coordinates.'
)
@click.option(
    '--browser_port',
    type=int,
    help='A number of port for browser messages.'
)
@click.option(
    '-v',
    '--verbose',
    is_flag=True,
    type=click.BOOL,
    help='Output detailed log messages.'
)
def main(bus_port, browser_port, verbose):
    logging.basicConfig(level=logging.ERROR)
    logger.setLevel(logging.INFO)
    if verbose:
        logger.setLevel(logging.DEBUG)
    trio.run(start_server, bus_port, browser_port)


if __name__ == '__main__':
    main()
