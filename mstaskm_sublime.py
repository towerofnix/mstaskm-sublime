# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
import urllib
import json
import threading
import sys

from .websocket import create_connection
from .websocket._exceptions import WebSocketConnectionClosedException

threads = []

class MstaskmMenuCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.edit = edit
        tasks = self.get_tasks()
        self.opts = ['--']
        self.rendered_opts = ['Nothing']
        for task_id in tasks:
            self.opts.append(task_id)
            self.rendered_opts.append(tasks[task_id]['name'])
        self.view.show_popup_menu(self.rendered_opts, self.on_select)

    def on_select(self, option):
        if option > 0:
            self.command(self.opts[option])

    def get_tasks(self):
        return json.loads(
            urllib.request.urlopen('http://localhost:8079/api/tasks')
                .read().decode('utf-8'))

    def ws_worker(self, cmd):
        def worker():
            win = sublime.active_window()
            self.panel = win.create_output_panel('mstaskm')
            self.panel.set_syntax_file(
                'Packages/mstaskm-sublime/mstaskm_output.tmLanguage')
            self.panel.settings().set('auto_indent', False)
            self.panel.settings().set('color_scheme',
                'Packages/mstaskm-sublime/mstaskm_output.tmTheme')
            ws = create_connection('ws://localhost:8079/' + cmd)
            win.run_command('show_panel', {'panel': 'output.mstaskm'})
            while True:
                try:
                    data = ws.recv()
                    code = data[0]
                    lines = data[1:].split('\n')
                    text = ''
                    for line in lines:
                        text += '[%s] %s\n' % (code, line)
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    self.panel.set_read_only(False)
                    self.panel.run_command('insert', {'characters': text})
                    self.panel.set_read_only(True)
                except WebSocketConnectionClosedException:
                    print('Closed')
                    break
        return worker

    def command(self, cmd):
        print('Running mstasmk command:', cmd)

        url = 'http://localhost:8079/api/run-task'

        data = json.dumps({'id': cmd}).encode('utf-8')

        req = urllib.request.Request(
            url, data, {'Content-Type': 'application/json'})

        response = urllib.request.urlopen(req)
        res_text = response.read().decode('utf-8')
        res_dict = json.loads(res_text)

        if 'success' in res_dict:
            print('Success!', res_dict['success'])
            t = threading.Thread(target=self.ws_worker(cmd))
            threads.append(t)
            t.start()
        elif 'error' in res_dict:
            print('Error..', res_dict['error'])
        else:
            print(res_dict)
