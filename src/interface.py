#!/usr/bin/env python3
# -*- python -*-
'''
nightshift - A terminal user interface for redshift
Copyright © 2014  Mattias Andrée (m@maandree.se)

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
    _button = lambda *i : ('[\033[1m%s\033[m]' if ui_state['focus'] in i else '<%s>')
    temperature =  tuple([red_temperature] + list(red_temperatures))
    brightness = [b * 100 for b in [red_brightness] + list(red_brightnesses)]
    print('\033[H', end = '')
    if red_running:
        lat, lon = red_location
        _if = lambda pn, v : pn[0] if v >= 0 else pn[1]
        print('\033[2KLocation: %.4f°%s %.4f°%s' % (abs(lat), _if('NS', lat), abs(lon), _if('EW', lon)))
        print('\033[2KTemperature: %.0f K (day: %.0f K, night: %.0f K)' % tuple(temperature))
        print('\033[2KBrightness: %.0f %% (day: %.0f %%, night: %.0f %%)' % tuple(brightness))
        print('\033[2KDayness: %.0f %%' % (red_period * 100))
        print('\033[2K' + ('Dying' if red_dying else ('Enabled' if red_status else 'Disabled')))
        print('\033[2K\n\033[2K', end = '')
        if not red_dying:
            if red_frozen:
                print(_button(0, 1) % 'Thaw', end = '  ')
                print(_button(2) % 'Kill', end = '  ')
                print(_button(3) % 'Close')
            else:
                print(_button(0) % ('Disable' if red_status else 'Enable'), end = '  ')
                print(_button(1) % 'Freeze', end = '  ')
                print(_button(2) % 'Kill', end = '  ')
                print(_button(3) % 'Close')
        else:
            print(_button(0, 1, 2) % 'Kill immediately', end = '  ')
            print(_button(3) % 'Close')
    else:
        print('\033[2KNot running')
        print('\033[2K\n\033[2K', end = '')
        print(_button(0, 1, 2) % 'Revive', end = '  ')
        print(_button(3) % 'Close')
    print('\033[J')


def ui_read():
    global red_dying, red_frozen
    inbuf = sys.stdin.buffer
    while True:
        c = inbuf.read(1)
        if c == b'q':
            break
        elif c == b'\t':
            red_condition.acquire()
            try:
                if red_running and not red_dying:
                    if red_frozen and (ui_state['focus'] == 0):
                        ui_state['focus'] = 1
                    ui_state['focus'] = (ui_state['focus'] + 1) % 4
                    if red_frozen and (ui_state['focus'] == 0):
                        ui_state['focus'] = 1
                elif ui_state['focus'] == 3:
                    ui_state['focus'] = 0
                else:
                    ui_state['focus'] = 3
                red_condition.notify()
            finally:
                red_condition.release()
        elif c in b' \n':
            red_condition.acquire()
            try:
                if ui_state['focus'] == 3:
                    break
                elif red_running:
                    if red_dying or (ui_state['focus'] == 2):
                        sock.sendall('kill\n'.encode('utf-8'))
                        red_dying = True
                    elif red_frozen:
                        sock.sendall('thaw\n'.encode('utf-8'))
                        red_frozen = False
                    else:
                        if ui_state['focus'] == 0:
                            sock.sendall('toggle\n'.encode('utf-8'))
                        elif ui_state['focus'] == 1:
                            sock.sendall('freeze\n'.encode('utf-8'))
                            red_frozen = True
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
    global red_period, red_location, red_status, red_running, red_dying, red_frozen
    if status is not None:
        brightness  = [float(status['%s brightness' % k])  for k in ('Current', 'Daytime', 'Night')]
        temperature = [float(status['%s temperature' % k]) for k in ('Current', 'Daytime', 'Night')]
        red_condition.acquire()
        try:
            red_brightness,  red_brightnesses = brightness[0],  tuple(brightness[1:])
            red_temperature, red_temperatures = temperature[0], tuple(temperature[1:])
            red_period   = float(status['Dayness'])
            red_location = (float(status['Latitude']), float(status['Longitude']))
            red_status   = status['Enabled'] == 'yes'
            red_running  = status['Running'] == 'yes'
            red_dying    = status['Dying']   == 'yes'
            red_frozen  = status['Frozen'] == 'yes'
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

