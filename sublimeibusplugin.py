# -*- coding: utf-8 -*-
import sublime
import sublime_plugin
import os
import json
from os.path import join
import sys
import subprocess
import re
import math

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
if BASE_PATH not in sys.path:
    sys.path += [BASE_PATH] + [join(BASE_PATH, 'sublimeibus')]

from sublimeibus.host import agent


class Logger(object):
    def __init__(self, name):
        self.name = name
        settings = sublime.load_settings('SublimeIBus.sublime-settings')
        self.enabled = settings.get('sublime_ibus_debug')

    def debug(self, log):
        if self.enabled:
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
        self.window_layout = None

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

    def set_cursor_location(self):
        if self.window_layout is None:
            return
        left, top = self.window_layout.cursor_location()
        height = self.window_layout.view.line_height()
        self.push('set_cursor_location(%d, %d, %d, 0, %d)' %
                  (status.id_no, left, top, height))


class WindowLayout:
    def __init__(self):
        self.window_id = None
        self.load_settings()

    def load_settings(self):
        self.settings = sublime.load_settings('SublimeIBus.sublime-settings')

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def cursor_location(self):
        if self.window_id is None:
            return [0, 0]

        cmd = ['xwininfo',
               '-display', os.environ.get('DISPLAY'),
               '-id', self.window_id]
        env = {'PATH': os.environ.get('PATH', '')}
        out, err = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=env).communicate()
        output = out.decode('utf-8')
        if err != b'':
            logger.debug(err)
            return [0, 0]
        m = re.search('Absolute upper-left X:\s*(\d+)', output)
        x_pos = m.group(1)
        m = re.search('Absolute upper-left Y:\s*(\d+)', output)
        y_pos = m.group(1)
        m = re.search('Width:\s*(\d+)', output)
        width = m.group(1)
        # logger.debug('window position x: ' + x_pos + ", y: " + y_pos + ", width: " + width)

        window = self.window = sublime.active_window()
        view = self.view = window.active_view()
        layout = window.get_layout()
        cols = len(layout['cols']) - 1
        g2d = self.make_list2d(self.get_group_list(window), cols)
        cursor = view.text_to_layout(view.sel()[0].a)
        viewport = view.viewport_position()
        all_views_width = sum(self.calc_group_offset_width(g2d, cols))
        side_bar = int(width) - all_views_width

        offset = self.calc_offset(window, view)

        offset_x = self.get_setting('sublime_ibus_offset_x')
        offset_y = self.get_setting('sublime_ibus_offset_y')

        left = offset_x + sum(offset[0]) + cursor[0] - viewport[0] + int(x_pos) + side_bar
        top = offset_y + sum(offset[1]) + cursor[1] - viewport[1] + int(y_pos)
        return [left, top]

    def make_list2d(self, lst, cols):
        assert (len(lst) % cols) == 0
        return [lst[i * cols:(i + 1) * cols] for i in range(len(lst) // cols)]

    def get_group_list(self, window):
        return [window.active_view_in_group(g) for g in range(window.num_groups())]

    def calc_group_offset_width(self, g2d, group_col):
        r = len(g2d)
        ret = []
        for x in range(group_col):
            for y in range(r):
                if g2d[y][x] is not None:
                    ret += self.calc_view_width(g2d, y, x)
                    break
            else:
                logger.debug('WindowLayout.calc_group_offset_width: there is empty view.')
        return ret

    def calc_view_width(self, g2d, row, col):
        view = self.view
        minimap = self.minimap_status()
        return self.calc_view_width_offset(g2d[row][col]) + [
            view.viewport_extent()[0],
            (minimap['width'] if minimap['visible'] else 0),
            self.get_setting('sublime_ibus_view_right_vscroll_width')
            ]

    def minimap_status(self):
        window = self.window
        view = self.view
        extent1 = view.viewport_extent()
        window.run_command('toggle_minimap')
        extent2 = view.viewport_extent()
        window.run_command('toggle_minimap')
        diff = extent2[0] - extent1[0]
        return {'visible': diff > 0, 'width': abs(diff)}

    def calc_view_width_offset(self, view):
        left_width = self.get_setting('sublime_ibus_view_left_icon_width')
        line_numbers = self.line_numbers_status(view)
        return [
            left_width,
            (line_numbers['width'] if line_numbers['visible'] else 0)
            ]

    def line_numbers_status(self, view):
        visible = view.settings().get('line_numbers')
        width = (self.calc_line_numbers_width(view) + 3
            if visible else 0)
        return {'visible': visible, 'width': width, 'mode': 'calc'}

    def calc_line_numbers_width(self, view):
        lines, _ = view.rowcol(view.size())
        c = self.get_number_column(lines + 1)
        return c * view.em_width()

    def get_number_column(self, n):
        return int(math.log10(n)) + 1

    def calc_offset(self, window, view):
        self.tabs = self.tabs_status(window, view)

        group, _ = window.get_view_index(view)
        layout = window.get_layout()
        _, c = self.get_layout_rowcol(layout)

        g2d = self.make_list2d(self.get_group_list(window), c)
        row, col = self.get_group_rowcol(layout, group)

        offset = [[], []]
        offset[0] += self.calc_group_offset_width(g2d, col)
        offset[1] += self.calc_group_offset_height(g2d, row)
        offset[0] += self.calc_view_width_offset(view)
        offset[1] += self.calc_view_height_offset(view)
        return offset

    def get_layout_rowcol(self, layout):
        c = len(layout['cols']) - 1
        r = len(layout['rows']) - 1
        return (r, c)

    def get_group_rowcol(self, layout, group):
        c = len(layout['cols']) - 1
        return (group // c, group % c)

    def calc_group_offset_height(self, g2d, group_row):
        c = len(g2d[0])
        ret = []
        for y in range(group_row):
            for x in range(c):
                if g2d[y][x] is not None:
                    ret += self.calc_view_height(g2d[y][x])
                    break
            else:
                logger.debug('WindowLayout.calc_group_offset_height: there is empty view.')
        return ret

    def calc_view_height(self, view):
        hscroll_bar = self.hscroll_bar_status(view)
        return self.calc_view_height_offset(view) + [
            view.viewport_extent()[1],
            (hscroll_bar['height'] if hscroll_bar['visible'] else 0)
            ]

    def hscroll_bar_status(self, view):
        word_wrap = view.settings().get('word_wrap')
        extent = view.viewport_extent()
        layout = view.layout_extent()
        diff = layout[0] - extent[0]
        return {
            'visible': diff > 0 and word_wrap != True,
            'height': self.get_setting('sublime_ibus_view_bottom_hscroll_height'),
            # 'diff': self.hscroll_bar_diff(view),
            }

    def calc_view_height_offset(self, view):
        return [self.tabs['height'] if self.tabs['visible'] else 0]

    def tabs_status(self, window, view):
        extent1 = view.viewport_extent()
        window.run_command('toggle_tabs')
        extent2 = view.viewport_extent()
        window.run_command('toggle_tabs')
        diff = extent2[1] - extent1[1]
        return {'visible': diff > 0, 'height': abs(diff)}


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
        if enable:
            command.set_cursor_location()

    def ibus_query_surrounding_text_cb(self, id_no, keyval, modmask, backslash, pressed):
        pass

    def ibus_update_preedit_text_cb(self, id_no, text, cursor_pos, visible, attributes):
        pass

    def ibus_commit_text_cb(self, id_no, text):
        if status.view is not None:
            status.view.run_command('ibus_insert', {"text": text})
            command.set_cursor_location()

    def ibus_hide_preedit_text_cb(self, id_no):
        pass

    def ibus_process_key_event_cb(self, id_no, handled):
        if handled == 0:
            settings = sublime.load_settings('SublimeIBusFallBackCommand.sublime-settings')
            cmd = settings.get(status.key)
            if cmd is not None:
                status.view.run_command(cmd.get('command', None),
                                        cmd.get('args', None))


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

        keysym = self.table.get(key, None)
        if keysym is not None:
            status.key = key
            command.process_key(keysym)


class IbusListener(sublime_plugin.EventListener):
    def on_activated(self, view):
        status.view = view

        # get active X Window ID
        cmd = ['xprop', '-root', '_NET_ACTIVE_WINDOW']
        env = {'PATH': os.environ.get('PATH', ''),
               'DISPLAY': os.environ.get('DISPLAY')}
        out, err = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=env).communicate()
        if err == b'':
            m = re.search('(0x[\da-f]+)', out.decode('utf-8'))
            window_id = m.group(1)
            # logger.debug(window_id)
            if command.window_layout is None:
                command.window_layout = WindowLayout()
            command.window_layout.window_id = window_id
            command.set_cursor_location()
        else:
            logger.debug(err)

    def on_selection_modified(self, view):
        if status.enable:
            command.set_cursor_location()

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
