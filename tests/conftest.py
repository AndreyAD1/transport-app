def pytest_addoption(parser):
    parser.addoption(
        '--server_host',
        required=True,
        type=str,
        help='A server address. Example: ws://127.0.0.1',
    )
    parser.addoption(
        '--browser_port',
        required=True,
        type=int,
        help='A port for browser messages',
    )
    parser.addoption(
        '--bus_port',
        required=True,
        type=int,
        help='A port for bus messages',
    )


def pytest_generate_tests(metafunc):
    for argument_name in ['server_host', 'browser_port', 'bus_port']:
        if argument_name in metafunc.fixturenames:
            metafunc.parametrize(
                argument_name,
                [metafunc.config.getoption(argument_name)]
            )
