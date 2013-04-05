# -*- coding: utf-8 -*-
import os
import subprocess
import logging
try:
    import _thread as thread
except ImportError:
    import thread


if os.name == "nt" and not hasattr(subprocess, 'STARTF_USESHOWWINDOW'):
    subprocess.STARTF_USESHOWWINDOW = subprocess._subprocess.STARTF_USESHOWWINDOW


class ProcessListener(object):
    def on_data(self, proc, data):
        pass

    def on_finished(self, proc):
        pass


class AsyncProcess(object):
    def __init__(self, arg_list, listener):

        self.listener = listener
        self.killed = False

        # Hide the console window on Windows
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self.proc = subprocess.Popen(arg_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, startupinfo=startupinfo, shell=False)

        if self.proc.stdout:
            thread.start_new_thread(self.read_stdout, ())

        if self.proc.stderr:
            thread.start_new_thread(self.read_stderr, ())

    def kill(self):
        if not self.killed:
            self.killed = True
            self.proc.terminate()
            self.listener = None

    def poll(self):
        return self.proc.poll() == None

    def exit_code(self):
        return self.proc.poll()

    def read_stdout(self):
        while True:
            data = os.read(self.proc.stdout.fileno(), 2 ** 15)

            if data != "":
                if self.listener:
                    self.listener.on_data(self, data)
            else:
                self.proc.stdout.close()
                if self.listener:
                    self.listener.on_finished(self)
                break

    def read_stderr(self):
        while True:
            data = os.read(self.proc.stderr.fileno(), 2 ** 15)

            if data != "":
                if self.listener:
                    self.listener.on_data(self, data)
            else:
                self.proc.stderr.close()
                break


class SynchronizationContextListener(ProcessListener):
    def __init__(self, chat):
        self.chat = chat
        try:
            import sublime

            def sync(callback):
                sublime.set_timeout(callback, 0)
            self.sync = sync
        except ImportError:

            def simple_call(callback):
                callback()
            self.sync = simple_call

        self.chat.handle_connect()

    def on_data(self, proc, data):
        def next():
            self.chat.handle_read(data)
        self.sync(next)

    def on_finished(self, proc):
        def next():
            self.chat.handle_close()
        self.sync(next)


class ProcessChat(object):
    def __init__(self):
        self.async = None
        self.received_data = []
        self.logger = logging.getLogger('ProcessChat')

    def start(self, cmd):
        self.logger.debug('start process %s', cmd)
        if self.async is None:
            listener = SynchronizationContextListener(self)
            self.async = AsyncProcess(cmd, listener)
        else:
            raise

    def stop(self):
        if self.async is not None:
            if self.async.poll():
                self.async.kill()
            self.async = None
        else:
            raise

    def send(self, data):
        if self.async is not None:
            return self.async.proc.stdin.write(data.encode('utf-8'))
        else:
            raise

    def push(self, data):
        self.send(data)

    def handle_read(self, data):
        buf = data.decode('utf-8')
        terminator = self.get_terminator()

        while True:
            index = buf.find(terminator)
            if index != -1:
                if index > 0:
                    self.collect_incoming_data(buf[:index])
                self.found_terminator()
                buf = buf[index + len(terminator):]
            else:
                self.collect_incoming_data(buf)
                break

    def collect_incoming_data(self, data):
        self.received_data.append(data)

    def set_terminator(self, term):
        self.terminator = term

    def get_terminator(self):
        return self.terminator

    def found_terminator(self):
        self.process_data(''.join(self.received_data))
        self.received_data = []

    def process_data(self, data):
        self.logger.debug('process_data() -> (%d)\n"""%s"""', len(data), data)

    def handle_connect(self):
        self.logger.debug('handle_connect()')

    def handle_close(self):
        self.logger.debug('handle_close()')


def main():
    import time
    logging.basicConfig(level=logging.DEBUG)
    p = ProcessChat()
    p.set_terminator('\n')
    p.start(["python", "-u", "sublime-ibus-agent.py"])
    time.sleep(1)
    p.push('list_active_engines()\n')
    time.sleep(1)
    p.stop()


if __name__ == "__main__":
    main()
