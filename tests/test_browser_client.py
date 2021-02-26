import json
import random

import pytest
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
            'errors': [f'Requires msgType specified'],
            'msgType': 'Errors'
        }
        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        assert json_response == expected_response, 'Invalid JSON'


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
        ({'msgType': 'errors'}, 'data'),
        (
            {
                'data': {
                    'east_lng': random.uniform(0, 90),
                    'north_lat': random.uniform(0, 90),
                    'south_lat': random.uniform(0, 90),
                    'west_lng': random.uniform(0, 90)
                }
            },
            'msgType'
        ),
    ]
)
async def test_absent_fields(message, absent_field_name):
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.get_message()
        await ws.send_message(json.dumps(message))
        response = await ws.get_message()
        expected_response = {
            'errors': [f'Requires {absent_field_name} specified'],
            'msgType': 'Errors'
        }
        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        assert json_response == expected_response, 'Invalid JSON'
