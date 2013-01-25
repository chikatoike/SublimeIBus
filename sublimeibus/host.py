# -*- coding: utf-8 -*-
import os
import time
import logging
from os.path import join
from async import ProcessChat


class ChatDelegate(ProcessChat):
    def __init__(self, agent=None):
        super(ChatDelegate, self).__init__()
        self.agent = agent

    def process_data(self, data):
        if self.agent is not None and self.agent.callback is not None:
            self.agent.callback(data)


class Agent(object):
    def __init__(self):
        self.runner = None
        self.callback = None

    def register_callback(self, callback):
        self.callback = callback

    def start(self, agent_dir):
        self.agent_dir = agent_dir
        if self.runner is None:
            self.runner = ChatDelegate(self)
            self.runner.start(["python", "-u", join(agent_dir, "sublime-ibus-agent.py")])

    def stop(self):
        if self.runner is not None:
            self.runner.stop()
            self.runner = None

    def restart(self, agent_dir):
        self.stop()
        self.start(agent_dir)

    def setup(self):
        self.push('list_active_engines()\n')
        self.push('create_imcontext()\n')
        # self.push('start_focus_observation(1000)\n')
        # self.push('set_engine(0, "anthy")\n')
        # self.push('process_key_event(0, 0x61, 0, False)\n')
        self.push('focus_in(0)\n')
        # self.push('update_frame_coordinates(50331843)\n')
        self.push('enable(0)\n')
        # self.push('set_cursor_location(0, 100, 100, 0, 14)\n')

    def push(self, data):
        self.runner.push(data)

    def feedkeys(self, keys):
        for k in keys:
            if not isinstance(k, int):
                k = ord(k)
            self.push('process_key_event(0, %d, 0, None, None)\n' % k)
            self.push('set_surrounding_text(0, "", 0, 0)\n')


agent = Agent()


def on_data(data):
    print(data.rstrip('\r\n').lstrip('\r\n'))


def main():
    logging.basicConfig(level=logging.DEBUG)
    agent.register_callback(on_data)
    agent.start(os.getcwd())
    time.sleep(2)
    agent.setup()
    agent.feedkeys('aiu')
    time.sleep(3)
    agent.stop()


if __name__ == "__main__":
    main()
