// once the document is ready, execute the following
$(document).ready(function() {
  // ================================= Utility functions ====================================

  function getCurrentDateTime() {
    /*
      Objective    : Return the user properly formatted date time for logging
      Future Scope : Make more user friendly
      */
    var monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December"
    ];

    var d = new Date();
    var currDate =
      d.getDate() + " " + monthNames[d.getMonth()] + " " + d.getFullYear();
    var currTime =
      d.getHours() +
      ":" +
      d.getMinutes() +
      ":" +
      d.getSeconds() +
      ":" +
      d.getMilliseconds();
    return "Logging Data " + " on " + currDate + " at " + currTime + "  ";
  }

  function disableAllButtons(status) {
    /*
      Objective   : Disable / Enable all the buttons based on Status
      Input Parameters: 
      Status  : Bool value. 
      If true, buttons are disabled.
      If False, buttons are enabled.
      Approach    : Simply set disabled attribute to status for all buttons.
      Usage       : Effective in Stop and wait specifically as only one packet is allowed at a time.
      */

    // Comment these in Sliding window
    // uncomment these in STOP AND WAIT
    $("#SenderDisconnectBtn").attr("disabled", status);
    $("#ReceiverDisconnectBtn").attr("disabled", status);
    $("#senderInputDataBtn").attr("disabled", status);
    $("#senderFrontendData").attr("disabled", status);
    $("#MiddleLayerDisconnectBtn").attr("disabled", status);
  }

  function randomNumberFromRange(min, max) {
    /*
      Objective : generate random number within the given range
      Input Parameters:
      Min : The minimum value for range
      Max : The maximum value for range
      */
    return Math.floor(Math.random() * (max - min + 1) + min);
  }

  // ========================  Establish Connection with Socket IO =============================

  // create a socket with localhost and port 5000
  var socket = io.connect(
    location.protocol + "//" + document.domain + ":" + location.port
  );

  socket.on("connect", function() {
    /*
      From : It's a Predefined event. Emitted by socketIO when receiver comes alive.
      Task : Initialise a connection with sender. Say Hi to sender.
      To   : connection request to Middle layer backend
      */

    disableAllButtons(false);
    $("#ReceiverLogs").append(
      "<br><br>" +
        $("<div/>")
          .text("Receiver Alive !")
          .html()
    );
    $("#ReceiverLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(
            getCurrentDateTime() + "Receiver requesting connection. Hi Sender!"
          )
          .html()
    );
    socket.emit("connectionRequestToMiddleLayerBackend", {
      data: "Hi Sender!"
    });
  });

  socket.on("connectionRequestToMiddleLayerFrontend", function(message) {
    /*
      From : connection request to Middle layer backend
      Task : say Hello to user
      To   : connection request to Sender Backend
      */

    $("#MiddleLayerLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(getCurrentDateTime() + "Intercepting : " + message["data"])
          .html()
    );
    socket.emit("connectionRequestToSenderBackend", { data: message["data"] });
  });

  socket.on("connectionRequestToSenderFrontend", function(message) {
    /*
      From : connection request to Sender Backend
      Task : say Hi to receiver. Accept connection.
      To   : None. Connection is now ready. Wait for events.
      */

    $("#SenderLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(getCurrentDateTime() + message["data"])
          .html()
    );
    return false;
  });

  // Inform user if connection fails
  socket.on("connection_failure", function(message) {
    $("#SenderLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(message.data)
          .html()
    );
    disableAllButtons(true);
    return false;
  });

  socket.on("server_started", function() {
    /*
      From : predefined server connect event
      Task : To inform user that server is now alive.
      To   : None. Wait for handshake. Then events
      */

    $("#SenderLogs").append(
      "<br><br>" +
        $("<div/>")
          .text("Server Started !")
          .html()
    );
    return false;
  });

  // ===================================== continuous Ping pong ========================================
  // Interval function that tests message latency by sending a "ping" message.
  // The server then responds with a "pong" message and the round trip time is measured.

  var ping_pong_times = [];
  var start_time;
  window.setInterval(function() {
    /*
      Task : Fires a ping every 1 second
      To   : HeyPing ( at backend )
      */
    start_time = new Date().getTime();
    socket.emit("HeyPing");
  }, 1000);

  socket.on("HeyPong", function() {
    /*
      From     : Hey Pong ( from backend )
      Task     : Calculates the latency and updates its value
      To       : None. Let Ping fire again. It'll update again
      Approach : When the pong is received, the time from the ping is stored, 
      and the average of the last 30 samples is average and displayed.  
      */
    var latency = new Date().getTime() - start_time;
    ping_pong_times.push(latency);
    ping_pong_times = ping_pong_times.slice(-30); // keep last 30 samples
    var sum = 0;
    for (var i = 0; i < ping_pong_times.length; i++) {
      sum += ping_pong_times[i];
    }
    $("#ping-pong").text(Math.round(10 * sum / ping_pong_times.length) / 10);
  });

  // ===================================== Transmission events ========================================

  $("form#senderInput").submit(function(event) {
    /*
      From : Sender Input Form  : Packet originates here
      Task : Sender Input form processing
      To   : Sender Backend
      */

    // sending to sender backend
    var info = $("#senderInputData").val();
    socket.emit("sendPacketToSenderBackend", { data: info });

    // disable buttons until acknowledgement is received of current packet
    disableAllButtons(true);
    return false;
  });

  socket.on("sendPacketToSenderFrontend", function(message) {
    /*
      From : Sender Backend
      Task : Sender Frontend, append Logs on sender side & start timer for this packet
      To   : Middle Layer Backend
      */

    $("#SenderLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(
            getCurrentDateTime() +
              "Sending : " +
              message["data"] +
              "( Packet #" +
              message["currentPacket"] +
              " )"
          )
          .html()
    );

    // start a time here
    setTimeout(function() {
      socket.emit("packetTimerBlast", {
        data: message["data"],
        currentPacket: message["currentPacket"]
      });
    }, 2000);

    socket.emit("SendPacketToMiddleLayerBackend", {
      data: message["data"],
      currentPacket: message["currentPacket"]
    });
  });

  socket.on("SendPacketToMiddleLayerFrontend", function(message) {
    /*
      From : Middle Layer Backend
      Task : Middle Layer Frontend, append Logs on middle layer & randomly drop packets
      To   : Receiver backend OR Crash Handler
      */

    // random function here. packet lost in transmission -> nothing received
    var randomNumber = randomNumberFromRange(-5, 10);
    if (randomNumber < 0) {
      // failed
      $("#MiddleLayerLogs").append(
        "<br><br>" +
          $("<div/>")
            .text(
              getCurrentDateTime() +
                "Intercepting : " +
                message["data"] +
                "( Packet #" +
                message["currentPacket"] +
                " )" +
                " (XX Crashed XX)"
            )
            .html()
      );
      socket.emit("PackedCrashedAtMiddleLayer");
    } else {
      // all good
      $("#MiddleLayerLogs").append(
        "<br><br>" +
          $("<div/>")
            .text(
              getCurrentDateTime() +
                "Intercepting : " +
                message["data"] +
                "( Packet #" +
                message["currentPacket"] +
                " )"
            )
            .html()
      );
      socket.emit("sendPacketToReceiverBackend", {
        data: message["data"],
        currentPacket: message["currentPacket"]
      });
    }
    return false;
  });

  socket.on("sendPacketToReceiverFrontend", function(message) {
    /*
      From : Receiver backend  : packet received here : Ack originates here
      Task : Receiver Frontend, append Logs at receiver
      To   : Send Acknowledgement to Middle Layer Backend
      */

    $("#ReceiverLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(
            getCurrentDateTime() +
              "Received : " +
              message["data"] +
              "( Packet #" +
              message["currentPacket"] +
              " )"
          )
          .html()
    );

    ackMessage = "Ack for Packet : " + message["data"];
    $("#ReceiverLogs").append(
      "<br>" +
        $("<div/>")
          .text(
            getCurrentDateTime() +
              "Sending : " +
              ackMessage +
              "( Ack #" +
              message["currentAck"] +
              " )"
          )
          .html()
    );
    socket.emit("sendAckToMiddleLayerBackend", {
      data: ackMessage,
      currentAck: message["currentAck"]
    });

    return false;
  });

  socket.on("packedNotReceivedByReceiver", function() {
    /*
      From : Packet Crash Handler
      Task : append failure Logs at receiver
      To   : Nothing, sender will auto timeout
      */

    $("#ReceiverLogs").append(
      "<br><br><br>" +
        $("<div/>")
          .text("Debug Log : Packet crashed ")
          .html()
    );
    return false;
  });

  socket.on("sendAckToMiddleLayerFrontend", function(message) {
    /*
      From : Received Ack Middle Layer Backend
      Task : append Ack Logs at Middle layer frontend
      To   : Pass Ack to Sender Backend
      */
    // random function here. Ack lost in transmission
    // Sender assumes packet has not reached nothing received
    var randomNumber = randomNumberFromRange(-5, 10);
    if (randomNumber < 0) {
      // failed
      $("#MiddleLayerLogs").append(
        "<br>" +
          $("<div/>")
            .text(
              getCurrentDateTime() +
                "Intercepting : " +
                "( Ack #" +
                message["currentAck"] +
                " )" +
                " XX CRASHED XX"
            )
            .html()
      );
      socket.emit("AckCrashedAtMiddleLayer", {
        currentAck: message["currentAck"]
      });
    } else {
      $("#MiddleLayerLogs").append(
        "<br>" +
          $("<div/>")
            .text(
              getCurrentDateTime() +
                "Intercepting : " +
                message["data"] +
                "( Ack #" +
                message["currentAck"] +
                " )"
            )
            .html()
      );
      socket.emit("sendAckToSenderBackend", {
        data: message["data"],
        currentAck: message["currentAck"]
      });
    }
  });

  socket.on("ackNotReceivedBySender", function() {
    /*
      From : Ack Crash Handler
      Task : append failure Logs at sender
      To   : Nothing, sender will auto timeout
      */

    $("#SenderLogs").append(
      "<br><br>" +
        $("<div/>")
          .text("Debug Log : Ack crashed ")
          .html()
    );
    return false;
  });

  socket.on("sendAckToSenderFrontend", function(message) {
    /*
      From : Received Ack from Sender Backend    : Ack received here
      Task : append Ack Logs at Sender frontend
      To   : None, one packet journey completed
      */

    $("#SenderLogs").append(
      "<br>" +
        $("<div/>")
          .text(
            getCurrentDateTime() +
              "Received : " +
              message["data"] +
              "( Ack #" +
              message["currentAck"] +
              " )"
          )
          .html()
    );
    // ack received - re enable the buttons
    disableAllButtons(false);
  });

  // =================================== Disconnection events =======================================

  $("form#SenderDisconnect").submit(function(event) {
    /*
      From : Sender Disconnect button
      Task : Disable all buttons
      To   : disconnect request (By sender)
      */

    socket.emit("disconnect_request", { data: "sender " });
    disableAllButtons(true);
    return false;
  });

  $("form#MiddleLayerDisconnect").submit(function(event) {
    /*
      From : Middle Layer 'Break Transmission' button
      Task : Disable all buttons
      To   : disconnect request (By Middle Layer)
      */

    socket.emit("disconnect_request", { data: "Middle Layer " });
    disableAllButtons(true);
    return false;
  });

  $("form#ReceiverDisconnect").submit(function(event) {
    /*
      From : Receiver Disconnect button
      Task : Disable all buttons
      To   : disconnect request (By Receiver)
      */

    socket.emit("disconnect_request", { data: "receiver " });
    disableAllButtons(true);
    return false;
  });

  socket.on("disconnecting_confirmation", function(message) {
    /*
      From : disconnection request backend
      Task : Append disconnection log to Sender, Receiver and Middle Layer
      To   : disconnect ( predefined ) : Terminates socket
      */

    $("#SenderLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(getCurrentDateTime() + message["data"])
          .html()
    );
    $("#MiddleLayerLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(getCurrentDateTime() + message["data"])
          .html()
    );
    $("#ReceiverLogs").append(
      "<br><br>" +
        $("<div/>")
          .text(getCurrentDateTime() + message["data"])
          .html()
    );
    socket.emit("disconnect");
  });

  // ===============================================================================================
});
