#!/usr/bin/env python3
"""Starts the survey server in a daemon thread so the PTY session stays alive."""
import threading, time
from http.server import HTTPServer
import simple_server  # runs init_db, defines SurveyHandler, TEMPLATES_DIR, etc.

port = 8802
server = HTTPServer(('0.0.0.0', port), simple_server.SurveyHandler)

def run():
    server.serve_forever()

t = threading.Thread(target=run, daemon=True)
t.start()
print(f'Survey server running on http://0.0.0.0:{port}')
print(f'         http://127.0.0.1:{port}')

try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    server.server_close()
    print('\nServer stopped.')
