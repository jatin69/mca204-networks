#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, disconnect
import time
import random

# Set this variable to "threading", "eventlet" or "gevent" 
# I used gevent
async_mode = None

# #############################  ### Initialise flask ######################################
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


# ########################### serve stop and wait events #############################

# ################################# Establish Connection  #####################################

# Accepting connection from client
@socketio.on('connect', namespace='/stop-and-wait')
def saw_server_coming_alive():
    """
    From : Predefined event connect. Called when server comes alive.
    Task : Initialise session variables
    To   : Server start message at frontend
    """
    session['currentPacket'] = 0
    session['currentAck'] = 0
    session['expectedAck'] = 0
    emit('server_started')
    # emit('complete_connection', {'data': 'Hi Receiver!'})


@socketio.on('connectionRequestToMiddleLayerBackend', namespace='/stop-and-wait')
def saw_connection_request_to_middle_layer_backend(message):
    """
    From : Receiver frontend after receiver said hi to sender
    Task : Simply pass data from receiver front end to middle layer frontend
    To   : Middle layer frontend - to display log
    """
    emit('connectionRequestToMiddleLayerFrontend', {'data': message['data']})


@socketio.on('connectionRequestToSenderBackend', namespace='/stop-and-wait')
def saw_connection_request_to_sender_backend(message):
    """
    From : Middle layer frontend
    Task : If receiver greets, then all good. Else, fail connection
    To   : Sender frontend - to display log
    """
    if message['data'] == 'Hi Sender!':
        emit('connectionRequestToSenderFrontend', {
             'data': 'Connection established. Hello Receiver!'})
    else:
        emit('connection_failure', {'data': 'Connection denied, Retry!'})


# ###################################### Ping Pong #######################################

@socketio.on('HeyPing', namespace='/stop-and-wait')
def saw_ping_pong():
    """
    From : ping
    Task : simply emit pong and help in roundtrip latency calculation 
    To   : pong
    """
    emit('HeyPong')

# ###################################### Transmission #######################################


@socketio.on('sendPacketToSenderBackend', namespace='/stop-and-wait')
def saw_handling_packet_at_sender_backend(message):
    """
    From : Sender Input form OR retransmissions
    Task : initialise session variables
    To   : send Packet to sender frontend
    """
    print(message)
    session['currentPacket'] = session.get('currentPacket', 0) + 1
    session['expectedAck'] = session['currentPacket']
    emit('sendPacketToSenderFrontend',  {
        'data': message['data'],
        'currentPacket': session['currentPacket']
    })


@socketio.on('packetTimerBlast', namespace='/stop-and-wait')
def saw_handling_timer_Blast_from_sender(message):
    """
    From : Sender Timer
    Task : If the acknowledgement of previous packet is successfully received. All good.
           else, re transmit the message 
    To   : Middle layer frontend
    """
    print("Timer Blasted for Packet #", message['currentPacket'])
    """
    Case : Missing Packet case
    Explanation : If current packet ( whose timer blasts after 2 seconds ) 
    is still greater (even after 2 seconds ) than 
    packets received by receiver (who should have received atleast 2 more in 2 seconds)
    then something is wrong. Retransmit.

    Case : Missing acknowledgement case
    Explanation : Ack is incremented from receiver side, but is never reached at sender.
    so we decrement the session currentAck whenver ack crashes at middle layer
    that way, currentExpectedAck (equal to currentPack for stop and wait) 
    is always > currentAck

    """
    if message['currentPacket'] > session['currentAck']:
        print("Resending Packet number", message['currentPacket'])
        emit('sendPacketToSenderFrontend', {
             'data': message['data'], 'currentPacket': message['currentPacket']})
    else:
        print("No issues. Packet number", message['currentPacket'], "successful.")


@socketio.on('SendPacketToMiddleLayerBackend', namespace='/stop-and-wait')
def saw_handling_packet_at_middle_layer_backend(message):
    """
    From : sender frontend
    Task : provide some visual delay
    To   : Middle layer frontend
    """
    time.sleep(.05)
    emit('SendPacketToMiddleLayerFrontend', {
         'data': message['data'], 'currentPacket': message['currentPacket']})
    time.sleep(.05)


@socketio.on('PackedCrashedAtMiddleLayer', namespace='/stop-and-wait')
def saw_handling_packet_crash_at_middle_layer():
    """
    From : Middle Layer frontend
    Task : handle packet crash and display debug log at frontend
    To   : Receiver frontend for debug log
    """
    emit('packedNotReceivedByReceiver')


@socketio.on('sendPacketToReceiverBackend', namespace='/stop-and-wait')
def saw_handling_packet_at_receiver_backend(message):
    """
    From : Middle layer frontend
    Task : packet successfully received. Increment the ackNumber to be sent.
    To   : Receiver frontend
    """
    session['currentAck'] = session.get('currentAck', 0) + 1
    emit('sendPacketToReceiverFrontend',
         {'data': message['data'], 'currentPacket': message['currentPacket'], 'currentAck': session['currentAck']})


@socketio.on('sendAckToMiddleLayerBackend', namespace='/stop-and-wait')
def saw_handling_ack_at_middle_layer_backend(message):
    """
    From : Receiver frontend
    Task : packet successfully received. Increment the ackNumber to be sent
    To   : Middle layer frontend
    """
    time.sleep(.05)
    emit('sendAckToMiddleLayerFrontend', {
         'data': message['data'], 'currentAck': message['currentAck']})
    time.sleep(.05)


@socketio.on('AckCrashedAtMiddleLayer', namespace='/stop-and-wait')
def saw_handling_ack_crash_at_middle_layer(message):
    """
    From : Middle Layer frontend
    Task : handle Ack crash and display debug log at frontend
    To   : Sender frontend for debug log
    """
    print("Ack #", message['currentAck'], "crashed.")
    session['currentAck'] = session['currentAck']-1
    emit('ackNotReceivedBySender')

@socketio.on('sendAckToSenderBackend', namespace='/stop-and-wait')
def saw_handling_ack_at_sender_backend(message):
    """
    From : Middle Layer frontend
    Task : Pass on the message and ackNumber
    To   : Sender frontend
    """
    emit('sendAckToSenderFrontend', {
         'data': message['data'], 'currentAck': message['currentAck']})


# ################################# Disconnection events #################################

# Requesting termination of connection
@socketio.on('disconnect_request', namespace='/stop-and-wait')
def saw_handling_disconnect_request_at_backend(message):
    """
    From : User requested connection termination
    Task : Tie the loose ends, the call the disconnect() event
    To   : disconnection frontend
    """
    emit('disconnecting_confirmation', {
         'data': message['data'] + 'Disconnected!'})


# Server disconnected
@socketio.on('disconnect', namespace='/stop-and-wait')
def saw_test_disconnect():
    """
    From : predefined disconnect event
    Task : Disconnect the server from client
    To   : None. Print logs to console.
    """
    print('Receiver disconnected', request.sid)



# ############################ Serving stop and wait #####################################

# when namespaces are ready - change it to @app.route('/selective-repeat')
@app.route('/stop-and-wait')
def saw_stop_and_wait():
    """
    From : User navigates to "localhost:5000" in a new tab
    Task : Serve the "templates/index.html" page to user
    To   : None. Wait for events to start.
    """
    return render_template('stop-and-wait.html', async_mode=socketio.async_mode)



# ################################ Serving go back N events ####################################

# ################################# Establish Connection  #####################################

# Accepting connection from client
@socketio.on('connect', namespace='/go-back-N')
def gbn_server_coming_alive():
    """
    From : Predefined event connect. Called when server comes alive.
    Task : Initialise session variables
    To   : Server start message at frontend
    """
    session['currentPacket'] = 0
    session['currentAck'] = 0
    session['expectedAck'] = 0
    session['lastReceivedAck'] = 0
    session['receivedAcks'] = []
    emit('server_started')
    # emit('complete_connection', {'data': 'Hi Receiver!'})


@socketio.on('connectionRequestToMiddleLayerBackend', namespace='/go-back-N')
def gbn_connection_request_to_middle_layer_backend(message):
    """
    From : Receiver frontend after receiver said hi to sender
    Task : Simply pass data from receiver front end to middle layer frontend
    To   : Middle layer frontend - to display log
    """
    emit('connectionRequestToMiddleLayerFrontend', {'data': message['data']})


@socketio.on('connectionRequestToSenderBackend', namespace='/go-back-N')
def gbn_connection_request_to_sender_backend(message):
    """
    From : Middle layer frontend
    Task : If receiver greets, then all good. Else, fail connection
    To   : Sender frontend - to display log
    """
    if message['data'] == 'Hi Sender!':
        emit('connectionRequestToSenderFrontend', {
            'data': 'Connection established. Hello Receiver!'})
    else:
        emit('connection_failure', {'data': 'Connection denied, Retry!'})


# ###################################### Ping Pong #######################################

@socketio.on('HeyPing', namespace='/go-back-N')
def gbn_ping_pong():
    """
    From : ping
    Task : simply emit pong and help in roundtrip latency calculation 
    To   : pong
    """
    emit('HeyPong')


# ###################################### Transmission #######################################


@socketio.on('sendPacketToSenderBackendBurst', namespace='/go-back-N')
def gbn_handling_packet_at_sender_backend_in_burst_mode(message):
    """
    From : Sender Input form OR retransmissions
    Task : initialise session variables
    To   : send Packet to sender frontend
    """
    print("Burst Mode Active. Initialise sliding window.")
    # print(message)
    initial = int(session.get('currentPacket', 0 )) + 1
    session['totalNumberOfPackets'] = int(message['totalNumberOfPackets']) + int(session.get('currentPacket', 0))
    session['slidingWindow'] = [ i+initial for i in range(int(message['windowSize']))]

    print(session['slidingWindow'])
    for packetNumber in session['slidingWindow']:
        gbn_handling_packet_at_sender_backend({
            'currentPacketNumber' : packetNumber
        })
        # time.sleep(.05)
        time.sleep(.05)


@socketio.on('sendPacketToSenderBackend', namespace='/go-back-N')
def gbn_handling_packet_at_sender_backend(message):
    """
    From : Sender Input form OR retransmissions
    Task : initialise session variables
    To   : send Packet to sender frontend
    """
    # session['currentPacket'] = session.get('currentPacket',0) + 1

    session['currentPacket'] = message["currentPacketNumber"]
    print("now ", session['currentPacket'])
    emit('sendPacketToSenderFrontend', {
        'data': 'D' + str(session['currentPacket']),
        'currentPacket': session['currentPacket']})
    session['expectedAck'] = session['currentPacket']
    

@socketio.on('packetTimerBlast', namespace='/go-back-N')
def gbn_handling_timer_Blast_from_sender(message):
    """
    From : Sender Timer
    Task : If the acknowledgement of previous packet is successfully received. All good.
           else, re transmit the message 
    To   : Middle layer frontend
    """
    print("Timer Blasted for Packet #", message['currentPacket'])
    """
    Case : Missing Packet case
    Explanation : If current packet ( whose timer blasts after 2 seconds ) 
    is still greater (even after 2 seconds ) than 
    packets received by receiver (who should have received atleast 2 more in 2 seconds)
    then something is wrong. Retransmit.

    Case : Missing acknowledgement case
    Explanation : Ack is incremented from receiver side, but is never reached at sender.
    so we decrement the session currentAck whenever ack crashes at middle layer
    that way, currentExpectedAck (equal to currentPack for stop and wait) 
    is always > currentAck

    Assumption : packet always come in sorted order

    """
    if message['currentPacket'] not in session['receivedAcks']:
        print("Resending Packet number", message['currentPacket'])
        emit('sendPacketToSenderFrontend', {
            'data': message['data'], 'currentPacket': message['currentPacket']})
    else:
        print("No issues. Packet number", message['currentPacket'], "successful.")


@socketio.on('SendPacketToMiddleLayerBackend', namespace='/go-back-N')
def gbn_handling_packet_at_middle_layer_backend(message):
    """
    From : sender frontend
    Task : provide some visual delay
    To   : Middle layer frontend
    """
    time.sleep(.05)
    emit('SendPacketToMiddleLayerFrontend', {
        'data': message['data'], 'currentPacket': message['currentPacket']})
    time.sleep(.05)


@socketio.on('PackedCrashedAtMiddleLayer', namespace='/go-back-N')
def gbn_handling_packet_crash_at_middle_layer():
    """
    From : Middle Layer frontend
    Task : handle packet crash and display debug log at frontend
    To   : Receiver frontend for debug log
    """
    emit('packedNotReceivedByReceiver')


@socketio.on('sendPacketToReceiverBackend', namespace='/go-back-N')
def gbn_handling_packet_at_receiver_backend(message):
    """
    From : Middle layer frontend
    Task : packet successfully received. Increment the ackNumber to be sent.
    To   : Receiver frontend
    """
    session['currentAck'] = int(message['currentPacket'])
    session['lastReceivedAck'] = session.get('lastReceivedAck',0)

    if(int(message['currentPacket']) == session['lastReceivedAck']+1):
        emit('sendPacketToReceiverFrontend', {
        'data': message['data'], 
        'currentPacket': message['currentPacket'], 
        'currentAck': session['currentAck']
        })
    else:
        emit('sendRejectedPacketToReceiverFrontend', {
        'data': message['data'], 
        'currentPacket': message['currentPacket'], 
        'currentAck': session['currentAck']
        })


@socketio.on('sendAckToMiddleLayerBackend', namespace='/go-back-N')
def gbn_handling_ack_at_middle_layer_backend(message):
    """
    From : Receiver frontend
    Task : packet successfully received. Increment the ackNumber to be sent
    To   : Middle layer frontend
    """
    time.sleep(.05)
    emit('sendAckToMiddleLayerFrontend', {
        'data': message['data'],
        'currentPacket' : message['currentPacket'],
         'currentAck': message['currentAck']})
    time.sleep(.05)


@socketio.on('AckCrashedAtMiddleLayer', namespace='/go-back-N')
def gbn_handling_ack_crash_at_middle_layer(message):
    """
    From : Middle Layer frontend
    Task : handle Ack crash and display debug log at frontend
    To   : Sender frontend for debug log
    """
    session['currentAck'] = int(session['currentAck'])-1 
    print("Ack #", message['currentAck'], "crashed.")
    emit('ackNotReceivedBySender', {
        'currentAck': message['currentAck']
    })
    

@socketio.on('sendAckToSenderBackend', namespace='/go-back-N')
def gbn_handling_ack_at_sender_backend(message):
    """
    From : Middle Layer frontend
    Task : Pass on the message and ackNumber
    To   : Sender frontend
    """
    emit('sendAckToSenderFrontend', {
        'data': message['data'], 'currentAck': message['currentAck']})
    
    # slide window as well
    # actual sliding will be probelmatic, so i just send next packet

    print("ack got", message["currentAck"])
    session['receivedAcks'].append(int(message['currentPacket']))
    session['lastReceivedAck'] = max(session['receivedAcks'])

    print("Nice job bro")
    if( int(session['currentPacket']) < int(session['totalNumberOfPackets'])):
        print("keep it up")
        gbn_handling_packet_at_sender_backend({
            'currentPacketNumber' : int(session['currentPacket']) + 1
        })
    else:
        # all done
        emit('sendCompletionMessage')


@socketio.on('sendNegAckToSenderBackend', namespace='/go-back-N')
def gbn_handling_negative_ack_at_sender_backend(message):
    """
    From : Middle Layer frontend
    Task : Pass on the message and ackNumber
    To   : Sender frontend
    """
    emit('sendNegAckToSenderFrontend', {
        'data': message['data'], 'currentPacket': message['currentPacket'] , 'currentAck': message['currentAck']})
    
    # slide window as well
    # actual sliding will be probelmatic, so i just send next packet
    
    gbn_handling_packet_at_sender_backend({
        'currentPacketNumber' : int(message['currentPacket'])
    })


# ################################# Disconnection events #################################

# Requesting termination of connection
@socketio.on('disconnect_request', namespace='/go-back-N')
def gbn_handling_disconnect_request_at_backend(message):
    """
    From : User requested connection termination
    Task : Tie the loose ends, the call the disconnect() event
    To   : disconnection frontend
    """
    emit('disconnecting_confirmation', {
        'data': message['data'] + 'Disconnected!'})


# Server disconnected
@socketio.on('disconnect', namespace='/go-back-N')
def gbn_test_disconnect():
    """
    From : predefined disconnect event
    Task : Disconnect the server from client
    To   : None. Print logs to console.
    """
    print('Receiver disconnected', request.sid)

# ########################### serve stop and wait #############################

@app.route('/go-back-N')
def gbn_go_back_N():
    """
    From : User navigates to "localhost:5000" in a new tab
    Task : Serve the "templates/index.html" page to user
    To   : None. Wait for events to start.
    """
    return render_template('go-back-N.html', async_mode=socketio.async_mode)


# ########################### serving selective repeat events #############################


# ################################# Establish Connection  #####################################

# Accepting connection from client
@socketio.on('connect', namespace='/selective-repeat')
def sr_server_coming_alive():
    """
    From : Predefined event connect. Called when server comes alive.
    Task : Initialise session variables
    To   : Server start message at frontend
    """
    session['currentPacket'] = 0
    session['currentAck'] = 0
    session['expectedAck'] = 0
    session['receivedAcks'] = []
    emit('server_started')
    # emit('complete_connection', {'data': 'Hi Receiver!'})


@socketio.on('connectionRequestToMiddleLayerBackend', namespace='/selective-repeat')
def sr_connection_request_to_middle_layer_backend(message):
    """
    From : Receiver frontend after receiver said hi to sender
    Task : Simply pass data from receiver front end to middle layer frontend
    To   : Middle layer frontend - to display log
    """
    emit('connectionRequestToMiddleLayerFrontend', {'data': message['data']})


@socketio.on('connectionRequestToSenderBackend', namespace='/selective-repeat')
def sr_connection_request_to_sender_backend(message):
    """
    From : Middle layer frontend
    Task : If receiver greets, then all good. Else, fail connection
    To   : Sender frontend - to display log
    """
    if message['data'] == 'Hi Sender!':
        emit('connectionRequestToSenderFrontend', {
            'data': 'Connection established. Hello Receiver!'})
    else:
        emit('connection_failure', {'data': 'Connection denied, Retry!'})


# ###################################### Ping Pong #######################################

@socketio.on('HeyPing', namespace='/selective-repeat')
def sr_ping_pong():
    """
    From : ping
    Task : simply emit pong and help in roundtrip latency calculation 
    To   : pong
    """
    emit('HeyPong')


# ###################################### Transmission #######################################


@socketio.on('sendPacketToSenderBackendBurst', namespace='/selective-repeat')
def sr_handling_packet_at_sender_backend_in_burst_mode(message):
    """
    From : Sender Input form OR retransmissions
    Task : initialise session variables
    To   : send Packet to sender frontend
    """
    print("Burst Mode Active. Initialise sliding window.")
    # print(message)
    initial = int(session.get('currentPacket', 0 )) + 1
    session['totalNumberOfPackets'] = int(message['totalNumberOfPackets']) + int(session.get('currentPacket', 0))
    session['slidingWindow'] = [ i+initial for i in range(int(message['windowSize']))]

    print(session['slidingWindow'])
    for packetNumber in session['slidingWindow']:
        sr_handling_packet_at_sender_backend({
            'currentPacketNumber' : packetNumber
        })
        time.sleep(.05)


@socketio.on('sendPacketToSenderBackend', namespace='/selective-repeat')
def sr_handling_packet_at_sender_backend(message):
    """
    From : Sender Input form OR retransmissions
    Task : initialise session variables
    To   : send Packet to sender frontend
    """
    # session['currentPacket'] = session.get('currentPacket',0) + 1

    session['currentPacket'] = message["currentPacketNumber"]
    print("now ", session['currentPacket'])
    emit('sendPacketToSenderFrontend', {
        'data': 'D' + str(session['currentPacket']),
        'currentPacket': session['currentPacket']})
    session['expectedAck'] = session['currentPacket']
    

@socketio.on('packetTimerBlast', namespace='/selective-repeat')
def sr_handling_timer_Blast_from_sender(message):
    """
    From : Sender Timer
    Task : If the acknowledgement of previous packet is successfully received. All good.
           else, re transmit the message 
    To   : Middle layer frontend
    """
    print("Timer Blasted for Packet #", message['currentPacket'])
    """
    Case : Missing Packet case
    Explanation : If current packet ( whose timer blasts after 2 seconds ) 
    is still greater (even after 2 seconds ) than 
    packets received by receiver (who should have received atleast 2 more in 2 seconds)
    then something is wrong. Retransmit.

    Case : Missing acknowledgement case
    Explanation : Ack is incremented from receiver side, but is never reached at sender.
    so we decrement the session currentAck whenever ack crashes at middle layer
    that way, currentExpectedAck (equal to currentPack for stop and wait) 
    is always > currentAck

    Assumption : packet always come in sorted order

    """
    print("received yet", session['receivedAcks'])
    if message['currentPacket'] not in session['receivedAcks']:
        print("Resending Packet number", message['currentPacket'])
        emit('sendPacketToSenderFrontend', {
            'data': message['data'], 'currentPacket': message['currentPacket']})
    else:
        print("No issues. Packet number", message['currentPacket'], "successful.")


@socketio.on('SendPacketToMiddleLayerBackend', namespace='/selective-repeat')
def sr_handling_packet_at_middle_layer_backend(message):
    """
    From : sender frontend
    Task : provide some visual delay
    To   : Middle layer frontend
    """
    time.sleep(.05)
    emit('SendPacketToMiddleLayerFrontend', {
        'data': message['data'], 'currentPacket': message['currentPacket']})
    time.sleep(.05)


@socketio.on('PackedCrashedAtMiddleLayer', namespace='/selective-repeat')
def sr_handling_packet_crash_at_middle_layer():
    """
    From : Middle Layer frontend
    Task : handle packet crash and display debug log at frontend
    To   : Receiver frontend for debug log
    """
    emit('packedNotReceivedByReceiver')


@socketio.on('sendPacketToReceiverBackend', namespace='/selective-repeat')
def sr_handling_packet_at_receiver_backend(message):
    """
    From : Middle layer frontend
    Task : packet successfully received. Increment the ackNumber to be sent.
    To   : Receiver frontend
    """
    session['currentAck'] = int(message['currentPacket'])
    emit('sendPacketToReceiverFrontend', {
        'data': message['data'], 
        'currentPacket': message['currentPacket'], 
        'currentAck': session['currentAck']
        })


@socketio.on('sendAckToMiddleLayerBackend', namespace='/selective-repeat')
def sr_handling_ack_at_middle_layer_backend(message):
    """
    From : Receiver frontend
    Task : packet successfully received. Increment the ackNumber to be sent
    To   : Middle layer frontend
    """
    time.sleep(.05)
    emit('sendAckToMiddleLayerFrontend', {
        'data': message['data'],
        'currentPacket' : message['currentPacket'],
         'currentAck': message['currentAck']})
    time.sleep(.05)


@socketio.on('AckCrashedAtMiddleLayer', namespace='/selective-repeat')
def sr_handling_ack_crash_at_middle_layer(message):
    """
    From : Middle Layer frontend
    Task : handle Ack crash and display debug log at frontend
    To   : Sender frontend for debug log
    """
    session['currentAck'] = int(session['currentAck'])-1 
    print("Ack #", message['currentAck'], "crashed.")
    emit('ackNotReceivedBySender', {
        'currentAck': message['currentAck']
    })
    

@socketio.on('sendAckToSenderBackend', namespace='/selective-repeat')
def sr_handling_ack_at_sender_backend(message):
    """
    From : Middle Layer frontend
    Task : Pass on the message and ackNumber
    To   : Sender frontend
    """
    emit('sendAckToSenderFrontend', {
        'data': message['data'], 'currentAck': message['currentAck']})
    
    # slide window as well
    # actual sliding will be probelmatic, so i just send next packet
    session['receivedAcks'].append(int(message['currentPacket']))

    print("Nice job bro")
    if( int(session['currentPacket']) < int(session['totalNumberOfPackets'])):
        print("keep it up")
        sr_handling_packet_at_sender_backend({
            'currentPacketNumber' : int(session['currentPacket']) + 1
        })
    else:
        # all done
        emit('sendCompletionMessage')


@socketio.on('sendNegAckToSenderBackend', namespace='/selective-repeat')
def sr_handling_negative_ack_at_sender_backend(message):
    """
    From : Middle Layer frontend
    Task : Pass on the message and ackNumber
    To   : Sender frontend
    """
    emit('sendNegAckToSenderFrontend', {
        'data': message['data'], 'currentPacket': message['currentPacket'] , 'currentAck': message['currentAck']})
    
    # slide window as well
    # actual sliding will be probelmatic, so i just send next packet
    
    sr_handling_packet_at_sender_backend({
        'currentPacketNumber' : int(message['currentPacket'])
    })


# ################################# Disconnection events #################################

# Requesting termination of connection
@socketio.on('disconnect_request', namespace='/selective-repeat')
def sr_handling_disconnect_request_at_backend(message):
    """
    From : User requested connection termination
    Task : Tie the loose ends, the call the disconnect() event
    To   : disconnection frontend
    """
    emit('disconnecting_confirmation', {
        'data': message['data'] + 'Disconnected!'})


# Server disconnected
@socketio.on('disconnect', namespace='/selective-repeat')
def sr_test_disconnect():
    """
    From : predefined disconnect event
    Task : Disconnect the server from client
    To   : None. Print logs to console.
    """
    print('Receiver disconnected', request.sid)



# ########################### serve selective repeat #############################

@app.route('/selective-repeat')
def sr_selective_repeat():
    """
    From : User navigates to "localhost:5000" in a new tab
    Task : Serve the "templates/index.html" page to user
    To   : None. Wait for events to start.
    """
    return render_template('selective-repeat.html', async_mode=socketio.async_mode)



# ############################ Serving index #####################################

# when namespaces are ready - change it to @app.route('/selective-repeat')
@app.route('/')
def index():
    """
    From : User navigates to "localhost:5000" in a new tab
    Task : Serve the "templates/index.html" page to user
    To   : None. Wait for events to start.
    """
    return render_template('index.html', async_mode=socketio.async_mode)



# ################################# Main function #####################################
import os

# Start the app : dev mode
if __name__ == '__main__':
    """
    Event : Start the server
    Task  : Keep the server running, debugging ON in dev mode
    """
    portis = os.environ.get('PORT')
    if(portis == None):
        portis = 5000
    else:
        portis = int(portis)
    print(portis)
    socketio.run(app, host= "0.0.0.0", port= portis, debug=False)

# ######################################################################################