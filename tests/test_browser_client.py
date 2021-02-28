from collections import Counter
import json
import random

import pytest
import trio
from trio_websocket import open_websocket_url


@pytest.mark.parametrize(
    'invalid_message',
    [
        '',
        'invalid_message',
    ]
)
async def test_invalid_browser_json(invalid_message):
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.get_message()
        await ws.send_message(invalid_message)
        response = await ws.get_message()
        expected_response = {
            'errors': ['Requires valid JSON'],
            'msgType': 'Errors'
        }
        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        assert json_response == expected_response, 'Invalid JSON'


async def test_empty_dict_json():
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.get_message()
        await ws.send_message('{}')
        response = await ws.get_message()
        expected_response = {
            'errors': [
                'Requires msgType specified',
            ],
            'msgType': 'Errors'
        }
        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        err_msg = 'Unexpected response'
        assert Counter(json_response) == Counter(expected_response), err_msg


async def test_empty_list_json():
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.get_message()
        await ws.send_message('[]')
        response = await ws.get_message()
        expected_response = {
            "errors": ["Requires a mapping JSON root element"],
            'msgType': 'Errors'
        }
        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        assert json_response == expected_response, 'Invalid JSON'


@pytest.mark.parametrize(
    ['message', 'absent_field_name'],
    [
        (
            {
                'msgType': 'newBounds',
                'data': {
                    'north_lat': random.uniform(-90, 90),
                    'south_lat': random.uniform(-90, 90),
                    'west_lng': random.uniform(-180, 180)
                }
            },
            'east_lng'
        ),
        (
            {
                'msgType': 'newBounds',
                'data': {
                    'east_lng': random.uniform(-90, 90),
                    'south_lat': random.uniform(-90, 90),
                    'west_lng': random.uniform(-180, 180)
                }
            },
            'north_lat'
        ),
        (
            {
                'msgType': 'newBounds',
                'data': {
                    'east_lng': random.uniform(-90, 90),
                    'north_lat': random.uniform(-90, 90),
                    'west_lng': random.uniform(-180, 180)
                }
            },
            'south_lat'
        ),
        (
            {
                'msgType': 'newBounds',
                'data': {
                    'east_lng': random.uniform(-180, 180),
                    'north_lat': random.uniform(-90, 90),
                    'south_lat': random.uniform(-90, 90)
                }
            },
            'west_lng'
        ),
    ]
)
async def test_absent_fields(message, absent_field_name):
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.get_message()
        await ws.send_message(json.dumps(message))
        response = await ws.get_message()
        expected_response = {
            'errors': {
                'data': {
                    absent_field_name: ['Missing data for required field.']
                }
            },
            'msgType': 'Errors'
        }
        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        assert json_response == expected_response, 'Invalid JSON'


@pytest.mark.de
@pytest.mark.parametrize(
    ['invalid_field', 'expected_error_msg'],
    [
        [{'south_lat': ''}, ['Not a valid number.']],
        [{'south_lat': []}, ['Not a valid number.']],
        [{'south_lat': {}}, ['Not a valid number.']],
        [
            {'south_lat': -90.1},
            [
                'Must be greater than or equal to -90 and less than or '
                'equal to 90.'
            ]
        ],
        [
            {'south_lat': 90.1},
            [
                'Must be greater than or equal to -90 and less than or '
                'equal to 90.'
            ]
        ],
        [{'north_lat': ''}, ['Not a valid number.']],
        [{'north_lat': []}, ['Not a valid number.']],
        [{'north_lat': {}}, ['Not a valid number.']],
        [
            {'north_lat': -90.1},
            [
                'Must be greater than or equal to -90 and less than or '
                'equal to 90.'
            ]
        ],
        [
            {'north_lat': 90.1},
            [
                'Must be greater than or equal to -90 and less than or '
                'equal to 90.'
            ]
        ],
        [{'west_lng': ''}, ['Not a valid number.']],
        [{'west_lng': []}, ['Not a valid number.']],
        [{'west_lng': {}}, ['Not a valid number.']],
        [
            {'west_lng': -180.1},
            [
                'Must be greater than or equal to -180 and less than or '
                'equal to 180.'
            ]
        ],
        [
            {'west_lng': 180.1},
            [
                'Must be greater than or equal to -180 and less than or '
                'equal to 180.'
            ]
        ],
        [{'east_lng': ''}, ['Not a valid number.']],
        [{'east_lng': []}, ['Not a valid number.']],
        [{'east_lng': {}}, ['Not a valid number.']],
        [
            {'east_lng': -180.1},
            [
                'Must be greater than or equal to -180 and less than or '
                'equal to 180.'
            ]
        ],
        [
            {'east_lng': 180.1},
            [
                'Must be greater than or equal to -180 and less than or '
                'equal to 180.'
            ]
        ],
    ]
)
async def test_invalid_window_coordinates(invalid_field, expected_error_msg):
    north_lat = random.uniform(-89, 90)
    east_lng = random.uniform(-179, 180)
    correct_data = {
        'east_lng': east_lng,
        'north_lat': north_lat,
        'south_lat': random.uniform(-90, north_lat),
        'west_lng': random.uniform(-180, east_lng)
    }
    invalid_data = {**correct_data, **invalid_field}
    invalid_message = {'msgType': 'newBounds', 'data': invalid_data}
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.get_message()
        await ws.send_message(json.dumps(invalid_message))
        with trio.move_on_after(2) as cancel_scope:
            response = await ws.get_message()

        if cancel_scope.cancelled_caught:
            error_message = 'Server does not respond if message was {}'
            assert False, error_message.format(invalid_message)

        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        expected_response = {
            'errors': {
                'data': {
                    list(invalid_field.keys())[0]: expected_error_msg
                }
            },
            'msgType': 'Errors'
        }
        assert json_response == expected_response, 'Unexpected response'
