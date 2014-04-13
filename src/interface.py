#!/usr/bin/env python3
# -*- python -*-
'''
nightshift - A terminal user interface for redshift
Copyright © 2014  Mattias Andrée (maandree@member.fsf.org)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import fcntl
import struct
import signal
import termios
import threading


ui_state = { 'focus' : 0
           }


def user_interface():
    '''
    Start user interface
    '''
    global red_condition
    red_condition = threading.Condition()
    ui_winch()
    daemon_thread(ui_status).start()
    daemon_thread(ui_refresh).start()
    
    print('\033[?1049h\033[?25l')
    saved_stty = termios.tcgetattr(sys.stdout.fileno())
    stty = termios.tcgetattr(sys.stdout.fileno())
    stty[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
    try:
        termios.tcsetattr(sys.stdout.fileno(), termios.TCSAFLUSH, stty)
        sock.sendall('status\n'.encode('utf-8'))
        ui_read()
    finally:
        termios.tcsetattr(sys.stdout.fileno(), termios.TCSAFLUSH, saved_stty)
        sys.stdout.buffer.write('\033[?25h\033[?1049l'.encode('utf-8'))
        sys.stdout.buffer.flush()


def ui_print():
    temperature =  tuple([red_temperature] + list(red_temperatures))
    brightness = [b * 100 for b in [red_brightness] + list(red_brightnesses)]
    print('\033[H\033[2J', end = '')
    if red_running:
        lat, lon = red_location
        _if = lambda pn, v : pn[0] if v >= 0 else pn[1]
        print('Location: %.4f°%s %.4f°%s' % (abs(lat), _if('NS', lat), abs(lon), _if('EW', lon)))
        print('Temperature: %.0f K (day: %.0f K, night: %.0f K)' % tuple(temperature))
        print('Brightness: %.0f %% (day: %.0f %%, night: %.0f %%)' % tuple(brightness))
        print('Dayness: %.0f %%' % (red_period * 100))
        print('Enabled' if red_status else 'Disabled')
        print()
        print(('[%s]' if ui_state['focus'] == 0 else '<%s>') % ('Disable' if red_status else 'Enable'), end='  ')
        print(('[%s]' if ui_state['focus'] == 1 else '<%s>') % 'Kill')
    else:
        print('Not running')
        print()
        print('[%s]' % 'Revive')


def ui_read():
    inbuf = sys.stdin.buffer
    while True:
        c = inbuf.read(1)
        if c == b'q':
            break
        elif c == b'\t':
            red_condition.acquire()
            try:
                ui_state['focus'] = 1 - ui_state['focus']
                red_condition.notify()
            finally:
                red_condition.release()
        elif c in b' \n':
            red_condition.acquire()
            try:
                if red_running:
                    if ui_state['focus'] == 0:
                        sock.sendall('toggle\n'.encode('utf-8'))
                    else:
                        sock.sendall('kill\n'.encode('utf-8'))
                    red_condition.notify()
                else:
                    respawn_daemon()
                    daemon_thread(ui_status).start()
                    sock.sendall('status\n'.encode('utf-8'))
                    sock.sendall('listen\n'.encode('utf-8'))
            finally:
                red_condition.release()


def ui_refresh():
    while True:
        red_condition.acquire()
        try:
            red_condition.wait()
            ui_print()
        finally:
            red_condition.release()


def ui_winch():
    global height, width
    (height, width) = struct.unpack('hh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '1234'))
    def winch(signal, frame):
        global height, width
        (height, width) = struct.unpack('hh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '1234'))
        red_condition.acquire()
        try:
            red_condition.notify()
        finally:
            red_condition.release()
    signal.signal(signal.SIGWINCH, winch)


def ui_status():
    buf = ''
    continue_to_run = True
    while continue_to_run:
        while '\n\n' not in buf:
            got = sock.recv(1024)
            if (got is None) or (len(got) == 0):
                continue_to_run = False
                break
            buf += got.decode('utf-8', 'replace')
            if '\n\n' in buf:
                break
        if continue_to_run:
            msg, buf = buf.split('\n\n')[0], '\n\n'.join(buf.split('\n\n')[1:])
            ui_status_callback(dict([line.split(': ') for line in msg.split('\n')]))
    ui_status_callback(None)


def ui_status_callback(status):
    global red_brightness, red_temperature, red_brightnesses, red_temperatures
    global red_period, red_location, red_status, red_running
    if status is not None:
        brightness = [float(status['%s brightness' % k]) for k in ('Current', 'Daytime', 'Night')]
        temperature = [float(status['%s temperature' % k]) for k in ('Current', 'Daytime', 'Night')]
        red_condition.acquire()
        try:
            red_brightness, red_brightnesses = brightness[0], tuple(brightness[1:])
            red_temperature, red_temperatures = temperature[0], tuple(temperature[1:])
            red_period = float(status['Dayness'])
            red_location = (float(status['Latitude']), float(status['Longitude']))
            red_status = status['Enabled'] == 'yes'
            red_running = status['Running'] == 'yes'
            red_condition.notify()
        finally:
            red_condition.release()
    else:
        red_condition.acquire()
        try:
            red_running = False
            red_condition.notify()
        finally:
            red_condition.release()


def daemon_thread(target, **kwargs):
    thread = threading.Thread(target = target, **kwargs)
    thread.setDaemon(True)
    return thread

