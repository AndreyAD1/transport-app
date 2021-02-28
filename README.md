# transport-app
The backend part of public transport application.

## Project Goal
This is the training project created to improve the skills of asynchronous code.
The training courses for web-developers - [dvmn.org](https://dvmn.org/).

##Getting Started
### Prerequisites
Python v3.9 should be already installed. 
Download a frontend web application [here](https://github.com/devmanorg/buses-on-the-map).
Download an archive containing bus route coordinates [here](https://dvmn.org/filer/canonical/1569857033/341/).

### How to Install
1. Download this repository;
2. use pip to install dependecies
```shell
pip install -r requirements.txt
```
Consider that a virtual environment provides better isolation.

### Quick Start
This repository contains a server and its client simulating buses. 
The server receives bus locations and sends them to the frontend application.
A linux command to run the server:
```shell
python server.py --bus_port 8080 --browser_port 8000
```
A linux command to run the client simulating buses:
```shell
python fake_bus.py ws://127.0.0.1:8080 --route_number 2000 --buses_per_route 3
```
Open [index.html](https://github.com/devmanorg/buses-on-the-map/blob/master/index.html) 
in Google Chrome.
If everything works fine, a browser will display moving buses on a map.

![transport-app](presentation.gif)

## Tests
A linux commands to run the tests:
```shell
pip install -r requirements-dev.txt
pytest tests --server_host ws://127.0.0.1 --bus_port 8080 --browser_port 8000
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
