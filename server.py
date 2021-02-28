from dataclasses import asdict, dataclass
from functools import partial
import json
import logging

import click
from marshmallow import Schema, fields, post_load, ValidationError, validate
import trio
from trio_websocket import serve_websocket, ConnectionClosed

logger = logging.getLogger(__file__)

COORDINATE_NAMES = ['south_lat', 'north_lat', 'west_lng', 'east_lng']
buses = {}
INVALID_JSON_MESSAGE = {
    'errors': ['Requires valid JSON'],
    'msgType': 'Errors'
}
MISSING_FIELD_MSG = ['Missing data for required field.']


class Error:
    def __init__(self, reasons):
        self.reasons = reasons

    def error_dict(self):
        error_dict = {
            'errors': self.reasons,
            'msgType': 'Errors'
        }
        return error_dict


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str


class BusSchema(Schema):
    busId = fields.Str(required=True, validate=validate.Length(min=1))
    lat = fields.Float(required=True, min=-90, max=90)
    lng = fields.Float(required=True, min=-180, max=180)
    route = fields.Str(required=True)

    @post_load
    def make_bus(self, bus_features, **kwargs):
        return Bus(**bus_features)


@dataclass
class WindowBounds:
    south_latitude: int = None
    north_latitude: int = None
    west_longitude: int = None
    east_longitude: int = None

    @classmethod
    def is_inside(cls, bus: Bus):
        window_coords = [
            cls.south_latitude,
            cls.north_latitude,
            cls.west_longitude,
            cls.east_longitude
        ]
        if not all(window_coords):
            logger.warning(f'Invalid window coordinates: {window_coords}')
            return False

        latitude_suits = cls.south_latitude <= bus.lat <= cls.north_latitude
        longitude_suits = cls.west_longitude <= bus.lng <= cls.east_longitude
        bus_is_inside_window = latitude_suits and longitude_suits
        return bus_is_inside_window

    @classmethod
    def update(cls, south_lat, north_lat, west_lng, east_lng):
        cls.south_latitude = south_lat
        cls.north_latitude = north_lat
        cls.west_longitude = west_lng
        cls.east_longitude = east_lng


class WindowBoundsSchema(Schema):
    south_lat = fields.Float(required=True, min=-90, max=90)
    north_lat = fields.Float(required=True, min=-90, max=90)
    west_lng = fields.Float(required=True, min=-180, max=180)
    east_lng = fields.Float(required=True, min=-180, max=180)

    @post_load
    def update_window_bounds(self, window_bounds, **kwargs):
        logger.debug(f'Update display bounds: {window_bounds}')
        return WindowBounds.update(**window_bounds)


class BrowserMessageSchema(Schema):
    msgType = fields.Str(required=True)
    data = fields.Nested(WindowBoundsSchema())


def parse_json_request(schema, request_body):
    error = None
    parsed_object = None
    try:
        parsed_object = schema.loads(request_body)
    except json.JSONDecodeError:
        logger.error(
            'Invalid request.  Can not unmarshal received message to JSON'
        )
        error = Error(['Requires valid JSON'])
    except ValidationError as ex:
        if ex.messages.get('_schema') == ['Invalid input type.']:
            error = Error(["Requires a mapping JSON root element"])
        elif MISSING_FIELD_MSG in ex.messages.values():
            missing_fields = [
                f for f, v in ex.messages.items() if v == MISSING_FIELD_MSG
            ]
            msg_template = 'Requires {} specified'
            error = Error([msg_template.format(f) for f in missing_fields])
        else:
            error = Error(ex.messages)

    return error, parsed_object


async def handle_bus_coordinates(request):
    websocket = await request.accept()
    bus_schema = BusSchema()
    while True:
        try:
            message = await websocket.get_message()
            logger.debug(f'Receive the bus message: {message}')
        except ConnectionClosed:
            logger.debug(f'Connection closed')
            break

        error, bus = parse_json_request(bus_schema, message)

        if error:
            await websocket.send_message(json.dumps(error.error_dict()))
            continue

        buses[bus.busId] = bus


async def send_to_browser(websocket):
    while True:
        buses_on_screen = [
            asdict(b) for b in buses.values() if WindowBounds.is_inside(b)
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
    browser_message_schema = BrowserMessageSchema()
    while True:
        try:
            browser_message = await websocket.get_message()
            logger.debug(f'Received browser message: {browser_message}')
        except ConnectionClosed:
            break

        error, _ = parse_json_request(browser_message_schema, browser_message)

        if error:
            await websocket.send_message(json.dumps(error.error_dict()))


async def talk_with_browser(request):
    ws = await request.accept()
    logger.debug(f'New browser connection has been established')
    async with trio.open_nursery() as nursery:
        sender = partial(send_to_browser, ws)
        listener = partial(listen_browser, ws)
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
