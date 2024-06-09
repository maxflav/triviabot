#!/usr/bin/python3

import socket
import sys
import threading
import time

from conf import config

class IRC:
    irc_socket = socket.socket()
    listener_thread = None
    handlers = []
    message_handlers = []
    last_message_times = []


    def __init__(self):
        self.irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handlers = [
            self.handle_privmsg,
            self.handle_ping,
            self.handle_unregistered,
            self.handle_registered,
            self.handle_nickname_in_use,
        ]

 
    def stop(self):
        self.listener_thread.stop()

 
    def send(self, msg):
        print("> " + msg)
        self.irc_socket.send(bytes(msg, "UTF-8"))

 
    def send_to_channel(self, channel, msg):
        self.send("PRIVMSG " + channel + " :" + msg + "\n")
 

    def connect(self):
        print("Connecting to: " + config.get('irc', 'server'))
        self.irc_socket.connect((config.get('irc', 'server'), config.get('irc', 'port')))

        self.listener_thread = threading.Thread(target=self.listen)
        self.listener_thread.start()

        self.send("USER " + config.get('irc', 'nick') + " " + config.get('irc', 'nick') +" " + config.get('irc', 'nick') + " :python\n")
        self.send("NICK " + config.get('irc', 'nick') + "\n")
        self.send("NICKSERV IDENTIFY " + config.get('irc', 'nickpass') + "\n")
        self.send("JOIN " + config.get('irc', 'channel') + "\n")


    def listen(self):
        while True:
            message = self.irc_socket.recv(2048)
            if not message:
                return

            message = message.decode("UTF-8")

            lines = message.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                print(line)
                for handler in self.handlers:
                    threading.Thread(target=handler, args=(line,)).start()

            time.sleep(0.1)


    def add_message_handler(self, handler):
        self.message_handlers.append(handler)


    def handle_ping(self, line):
        if not line.startswith("PING"):
            return

        self.send('PONG ' + line[5:] + '\r\n')


    def handle_unregistered(self, line):
        if not (":This nickname is registered" in line or ":You have not registered." in line):
            return

        time.sleep(0.1)
        self.send(f"NICKSERV IDENTIFY {config.get('irc', 'nickpass')}\n")

    def handle_nickname_in_use(self, line):
        if not ":Nickname is already in use." in line:
            return

        time.sleep(0.1)
        self.send(f"NICKSERV GHOST {config.get('irc', 'nick')} {config.get('irc', 'nickpass')}\n")


    def handle_registered(self, line):
        if not (":Password accepted" in line or ":Your nickname is not registered" in line):
            return

        time.sleep(0.1)
        self.send("JOIN " + config.get('irc', 'channel') + "\n")


    def handle_privmsg(self, line):
        if not "PRIVMSG" in line:
            return

        parts = line.split(" ")
        if len(parts) <= 3:
            return

        full_user = parts[0]
        user_parts = full_user.split("!")
        username = user_parts[0][1:]
        channel = parts[2]
        message = " ".join(parts[3:])[1:]

        for handler in self.message_handlers:
            handler(username, channel, message, full_user)
