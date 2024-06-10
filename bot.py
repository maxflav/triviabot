#!/usr/bin/python3

if __name__ == "__main__":
    print("Run main.py, not bot.py")
    exit(1)

from collections import defaultdict
import csv
from random import choice, random
import threading
import time

from tinydb import TinyDB, Query

from irc import *
from conf import config

db = TinyDB(config.get('trivia', 'scores_db'))
query = Query()

lock = threading.Lock()

BOLD = ""
BLUE = "12"
GREEN = "03"

INVISIBLE = "​"


def unping(username):
    return username[0] + INVISIBLE + username[1:]


class TriviaBot:
    def __init__(self):
        self.irc = IRC()

        self.botnick = config.get('irc', 'nick')
        self.channel = config.get('irc', 'channel')

        self.running = False

        self.question_start_time = 0
        self.current_question = None
        self.last_guess_time = None

        self.current_answer = None
        self.current_score_value = 0
        self.current_hint = None

        self.questions = []

        with open(config.get('trivia', 'questions_path')) as questions_file:
            for question, answer in csv.reader(questions_file):
                self.questions.append((question, answer))

        self.irc.add_message_handler(self.message_handler)
        self.irc.add_message_handler(self.admin_commands)
        self.irc.add_message_handler(self.user_commands)


    def start(self):
        self.irc.connect()


    def is_idle(self):
        idle_timeout = config.get('trivia', 'idle_timeout')
        if not idle_timeout:
            return False

        return time.time() - self.last_guess_time > idle_timeout


    def start_new_question(self):
        with lock:
            if not self.running:
                return

            self.current_question, self.current_answer = choice(self.questions)
            self.question_start_time = time.time()

            self.irc.send_to_channel(self.channel, f"{GREEN}{self.current_question}")

            threading.Thread(target=self.show_hints, args=(self.question_start_time, 0)).start()


    def show_hints(self, question_start_time, hint_level):
        times_up = False

        with lock:
            if self.current_question is None or self.question_start_time != question_start_time:
                return

            if hint_level == 3:
                times_up = True
                self.irc.send_to_channel(self.channel, f"Time's up! The answer was: {BOLD}{self.current_answer}")

                self.current_question = None
                self.current_answer = None
            elif hint_level == 0:
                self.current_hint = ""
                for char in self.current_answer:
                    if char.isalpha() or char.isdigit():
                        self.current_hint += '*'
                    else:
                        self.current_hint += char
            else:
                new_hint = ""
                for i in range(len(self.current_answer)):
                    if random() < 0.25:
                        new_hint += self.current_answer[i]
                    else:
                        new_hint += self.current_hint[i]
                self.current_hint = new_hint

            if not times_up:
                self.irc.send_to_channel(self.channel, f"Hint {hint_level+1}: {BLUE}{self.current_hint}")
                self.current_score_value = config.get("trivia", "scores")[hint_level]


        if times_up:
            if self.is_idle():
                self.irc.send_to_channel(self.channel, "Stopping due to inactivity. Use !start to start the bot again.")
                self.stop_trivia()
            else:
                time.sleep(config.get("trivia", "secs_between_questions"))
                self.start_new_question()
        else:
            time.sleep(config.get("trivia", "secs_between_hints"))
            self.show_hints(question_start_time, hint_level+1)


    def get_user_score(self, username):
        query_result = db.get(query.username == username)
        if query_result is None:
            return 0
        else:
            return query_result['score']


    def set_user_score(self, username, score):
        db.upsert({'username': username, 'score': score}, query.username == username)


    def message_handler(self, username, channel, message, full_user):
        self.last_guess_time = time.time()

        with lock:
            if not self.running:
                return

            if self.current_question is None:
                return

            if self.current_answer.lower() not in message.lower():
                return

            user_score = self.get_user_score(username) + self.current_score_value
            self.set_user_score(username, user_score)
            self.irc.send_to_channel(channel, f"{username}, {BOLD}{self.current_answer}{BOLD} is correct! You got {self.current_score_value} points for a total of {user_score}.")

            self.current_question = None
            self.current_answer = None

        time.sleep(config.get("trivia", "secs_between_questions"))
        self.start_new_question()


    def stop_trivia(self):
        self.running = False
        self.current_question = None
        self.current_answer = None


    def start_trivia(self):
        self.running = True
        self.last_guess_time = time.time()
        self.start_new_question()


    def admin_commands(self, username, channel, message, full_user):
        if full_user != config.get('admin'):
            return

        command_key = config.get('command_key')
        if not message.startswith(command_key):
            return

        parts = message.split(" ")
        command = parts[0][len(command_key):]
        args = "".join(parts[1:])

        if command == "reload_config":
            config.reload()
            self.irc.send_to_channel(channel, "Reloaded config")


    def user_commands(self, username, channel, message, full_user):
        command_key = config.get('command_key')
        if not message.startswith(command_key):
            return

        parts = message.split(" ")
        command = parts[0][len(command_key):]
        args = "".join(parts[1:])

        if command == "start":
            if self.running:
                return

            self.irc.send_to_channel(channel, "Starting Trivia")
            self.start_trivia()


        elif command == "stop":
            if not self.running:
                return

            self.irc.send_to_channel(channel, "Stopping Trivia")
            self.stop_trivia()

        elif command in ["points", "score"]:
            if len(args) > 0:
                for_user = args
            else:
                for_user = username

            score = self.get_user_score(for_user)
            self.irc.send_to_channel(channel, f"{for_user} has {BOLD}{score}{BOLD} points.")

        elif command in ["scores", "lifetime"]:
            top_10 = sorted(db.all(), key=lambda row: row['score'], reverse=True)[:10]
            self.irc.send_to_channel(channel,
                "    ".join(
                    f"{place+1}. {BOLD}{unping(row['username'])}{BOLD} {row['score']}"
                    for (place, row) in enumerate(top_10)
                )
            )

        elif command in ["daily", "weekly", "monthly"]:
            self.irc.send_to_channel(channel, f"{command} is not implemented yet, try {command_key}scores")

        elif command == "help":
            self.irc.send_to_channel(channel, f"Trivia bot created by maxle. This is a work in progress.")
            self.irc.send_to_channel(channel, f"Bot commands: !start !stop !score !scores")
