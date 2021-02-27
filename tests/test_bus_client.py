from collections import Counter
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
async def test_invalid_bus_json(invalid_message):
    async with open_websocket_url('ws://127.0.0.1:8080') as ws:
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
    async with open_websocket_url('ws://127.0.0.1:8080') as ws:
        await ws.send_message('{}')
        response = await ws.get_message()
        expected_response = {
            'errors': [
                'Requires route specified',
                'Requires busId specified',
                'Requires lng specified',
                'Requires lat specified'
            ],
            'msgType': 'Errors'
        }
        try:
            json_response = json.loads(response)
        except json.JSONDecodeError:
            assert False, f'Can not unmarshal response to JSON: {response}'

        expected_errors = expected_response['errors']
        returned_errors = json_response['errors']
        valid_errors = Counter(returned_errors) == Counter(expected_errors)
        assert valid_errors, 'Unexpected error list'

        expected_response.pop('errors')
        json_response.pop('errors')
        assert json_response == expected_response, 'Unexpected response body'


async def test_empty_list_json():
    async with open_websocket_url('ws://127.0.0.1:8080') as ws:
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
    'absent_field_name',
    [
        'busId',
        'lat',
        'lng',
        'route'
    ]
)
async def test_absent_bus_features(absent_field_name):
    message = {
        'busId': 'Test',
        'lat': random.uniform(0, 90),
        'lng': random.uniform(0, 90),
        'route': 'Test Route name'
    }
    message.pop(absent_field_name)
    async with open_websocket_url('ws://127.0.0.1:8080') as ws:
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
