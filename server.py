from dataclasses import asdict, dataclass, fields
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
INVALID_JSON_MESSAGE = {
    'errors': ['Requires valid JSON'],
    'msgType': 'Errors'
}


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str


@dataclass
class WindowBounds:
    south_latitude = None
    north_latitude = None
    west_longitude = None
    east_longitude = None

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


def verify_request_body_is_json(request_body):
    try:
        json.loads(request_body)
    except json.JSONDecodeError:
        logger.error(
            'Invalid request.  Can not unmarshal received message to JSON'
        )
        return INVALID_JSON_MESSAGE


def verify_received_json(received_json, required_feature_names):
    error_msg = {}
    for feature_name in required_feature_names:
        try:
            feature = received_json.get(feature_name)
        except AttributeError:
            logger.error('The root element of received JSON is a list')
            error_msg = {
                "errors": ["Requires a mapping JSON root element"],
                "msgType": "Errors"
            }
            break

        if feature is None:
            logger.error(f'No key "{feature_name}" is in the received JSON')
            error_msg = {
                "errors": [f"Requires {feature_name} specified"],
                "msgType": "Errors"
            }
            break

    return error_msg


async def handle_bus_coordinates(request):
    websocket = await request.accept()
    while True:
        try:
            message = await websocket.get_message()
            logger.debug(f'Receive the bus message: {message}')
        except ConnectionClosed:
            logger.debug(f'Connection closed')
            break

        err_msg = verify_request_body_is_json(message)
        if err_msg:
            await websocket.send_message(json.dumps(err_msg))
            continue

        bus_info = json.loads(message)
        err_msg = verify_received_json(bus_info, [f.name for f in fields(Bus)])
        if err_msg:
            await websocket.send_message(json.dumps(err_msg))
            continue

        buses[bus_info['busId']] = Bus(
            bus_info['busId'],
            bus_info['lat'],
            bus_info['lng'],
            bus_info['route']
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

        err_msg = verify_request_body_is_json(browser_message)
        if err_msg:
            await websocket.send_message(json.dumps(err_msg))
            continue

        browser_json_msg = json.loads(browser_message)
        err_msg = verify_received_json(browser_json_msg, ['msgType', 'data'])
        if err_msg:
            await websocket.send_message(json.dumps(err_msg))
            continue

        if browser_json_msg['msgType'] == 'newBounds':
            new_window_bounds = browser_json_msg['data']
            err_msg = verify_received_json(new_window_bounds, COORDINATE_NAMES)
            if err_msg:
                await websocket.send_message(json.dumps(err_msg))

            window_bounds.update(
                new_window_bounds['south_lat'],
                new_window_bounds['north_lat'],
                new_window_bounds['west_lng'],
                new_window_bounds['east_lng']
            )
            logger.debug(f'Update display bounds: {window_bounds}')


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
