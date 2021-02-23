import json

from trio_websocket import open_websocket_url


async def test_invalid_bus_json():
    async with open_websocket_url('ws://127.0.0.1:8000') as ws:
        await ws.send_message('invalid message')
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


