# -*- coding: utf-8 -*-
import sublime
import sublime_plugin
import os
import json
from os.path import join
import sys

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
if BASE_PATH not in sys.path:
    sys.path += [BASE_PATH] + [join(BASE_PATH, 'sublimeibus')]

from sublimeibus.host import agent


class Logger(object):
    def __init__(self, name):
        self.name = name

    def debug(self, log):
        print(self.name + ':' + str(log))


# import logging
# logger = logging.getLogger('SublimeIBus')
logger = Logger('SublimeIBus')


class IBusStatus(object):
    def __init__(self):
        self.enable = False
        self.view = None
        self._id_no = -1

    def id_no():
        def fget(self):
            return self._id_no

        def fset(self, value):
            self._id_no = value

        return locals()
    id_no = property(**id_no())

    def set_status(self, enable, view=None, engine_name=None):
        if view is None:
            view = self.view
        if view is None:
            view = sublime.active_window().active_view()

        self.enable = enable
        view.settings().set('ibus_mode', self.enable)

        if self.enable:
            view.set_status('ibus_mode', 'iBus: ' + engine_name)
        else:
            view.erase_status('ibus_mode')


class IBusCommand(object):
    def __init__(self, agent):
        self.agent = agent

    def push(self, data):
        # logger.debug('push: ' + repr(data))
        self.agent.push(data + '\n')

    def setup(self):
        # self.push('list_active_engines()')
        self.push('create_imcontext()')
        # wait for ibus_create_imcontext_cb

    def setup2(self):
        self.push('start_focus_observation(1000)')
        self.push('focus_in(%d)' % status.id_no)
        self.set_status(False)

    def set_status(self, enable):
        if enable:
            self.push('enable(%d)' % status.id_no)
        else:
            self.push('disable(%d)' % status.id_no)

    def process_key(self, keysym):
        self.push('process_key_event(0, %d, 0, None, None)' % keysym)
        # self.push('set_surrounding_text(0, "", 0, 0)')


class IBusCallback(object):
    def execute(self, command, args):
        if hasattr(self, command):
            cb = getattr(self, command)
            if isinstance(args, list):
                cb(*args)
            elif isinstance(args, dict):
                cb(**args)
            else:
                assert False
        else:
            logger.debug('unknown command: ' + repr({command: args}))

    def error(self, message):
        print('sublime-ibus-agent.py: ' + message)

    def setq(self, *args):
        pass

    def ibus_create_imcontext_cb(self, id_no):
        status.id_no = id_no
        command.setup2()

    def ibus_start_focus_observation_cb(self, id):
        pass

    def ibus_focus_changed_cb(self, id):
        pass

    def ibus_redo_focus_in_cb(self):
        pass

    def ibus_status_changed_cb(self, id_no, engine_name):
        enable = engine_name is not None
        status.set_status(enable, None, engine_name)

    def ibus_query_surrounding_text_cb(self, id_no, keyval, modmask, backslash, pressed):
        pass

    def ibus_update_preedit_text_cb(self, id_no, text, cursor_pos, visible, attributes):
        pass

    def ibus_commit_text_cb(self, id_no, text):
        if status.view is not None:
            status.view.run_command('ibus_insert', {"text": text})

    def ibus_hide_preedit_text_cb(self, id_no):
        pass

    def ibus_process_key_event_cb(self, id_no, handled):
        pass


class IbusToggleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        command.set_status(not status.enable)
        # logger.debug('enable = ' + str(enable))


class IbusKeyCommand(sublime_plugin.TextCommand):
    def __init__(self, view):
        super(IbusKeyCommand, self).__init__(view)
        self.table = sublime.load_settings('SublimeIBusKeyTable.sublime-settings')

    def run(self, edit, key, alt=False, ctrl=False, shift=False, super=False):
        if self.view.settings().get('is_widget'):
            return

        # TODO Why required this?
        command.set_status(True)

        keysym = self.table.get(key, None)
        if keysym is not None:
            command.process_key(keysym)


class IbusListener(sublime_plugin.EventListener):
    def on_activated(self, view):
        status.view = view

    # def on_deactivated(self, view):
    #     if status.enable:
    #         status.set_status(False)


class IbusInsertCommand(sublime_plugin.TextCommand):
    def run(self, edit, text):
        self.view.insert(edit, self.view.sel()[0].a, text)


def proc_callback(cmdobj):
    if 'message' in cmdobj:
        logger.debug('message: ' + cmdobj['message'])
    elif 'command' in cmdobj:
        IBusCallback().execute(cmdobj['command'], cmdobj['args'])
    else:
        assert False


def on_data(data):
    if data.find('{') != 0:
        logger.debug('message: ' + data)
    else:
        try:
            proc_callback(json.loads(data))
        except ValueError as e:
            logger.debug('error: ' + str(e))
            logger.debug(repr(data))


agent.register_callback(on_data)
agent.restart(join(BASE_PATH, 'sublimeibus'))

status = IBusStatus()
command = IBusCommand(agent)
command.setup()
