# mca204-networks

[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)

Standard Networking Protocols using [flask socketIO](https://github.com/miguelgrinberg/Flask-SocketIO/tree/master/example)

For more details, refer the [detailed readme](./README-detailed.md)

## How to run

* git clone the repo and navigate to directory
* make sure you have pipenv installed, or run `brew install pipenv`
* type `pipenv shell` to activate the virtual environment
* install requirements from `requirements.txt` or pip lock file
* run `python app.py` and navigate to `localhost:5000` in browser
* disable debugging in `app.py` if you don't want messages in terminal
* similarly, run `stop-and-wait.py`, `go-back-N.py`, and `selective-repeat.py`

## Transmission Flow

0.  Hi sender & Hi receiver - both connected
1.  Packet forms at senderFrontend
1.  SendPacketToMiddleLayerBackend
1.  SendPacketToMiddleLayerFrontend
1.  SendPacketToReceiverBackend
1.  sendPacketToReceiverFrontend
1.  sendAckToMiddleLayerBackend
1.  sendAckToMiddleLayerFrontend
1.  sendAckToSenderBackend
1.  sendAckToSenderFrontend

## Future scope

* colors for ack, message, and crashes
* put socketIO functions in separate file if possible
* Improve UI design : status in scrollable table format
