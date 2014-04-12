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


def user_interface():
    '''
    Start user interface
    '''
    print('\033[?1049h\033[?25l')
    saved_stty = termios.tcgetattr(sys.stdout.fileno())
    stty = termios.tcgetattr(sys.stdout.fileno())
    stty[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
    try:
        termios.tcsetattr(sys.stdout.fileno(), termios.TCSAFLUSH, stty)
        (height, width) = struct.unpack('hh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '1234'))
        sock.sendall('status\n'.encode('utf-8'))
        def winch(signal, frame):
            nonlocal height, width
            (height, width) = struct.unpack('hh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '1234'))
        signal.signal(signal.SIGWINCH, winch)
        def callback(status):
            if status is None:
                return
            print('\033[H\033[2J', end = '')
            for key in status:
                print(key + ': ' + status[key])
            print(str(width) + ' x ' + str(height))
            #brightness = [float(status['%s brightness' % k]) for k in ('Night', 'Current', 'Daytime')]
            #temperature = [float(status['%s temperature' % k]) for k in ('Night', 'Current', 'Daytime')]
            #dayness = float(status['Dayness'])
            #enabled = status['Enabled'] == 'yes'
            #running = status['Running'] == 'yes'
            #location = [float(status['Latitude']), float(status['Longitude'])]
        thread = threading.Thread(target = ui_status, args = (callback,))
        thread.setDaemon(True)
        thread.start()
        
        input()
    except:
        pass
    finally:
        termios.tcsetattr(sys.stdout.fileno(), termios.TCSAFLUSH, saved_stty)
        print('\033[?25h\033[?1049l')


def ui_status(callback):
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
            callback(dict([line.split(': ') for line in msg.split('\n')]))
    callback(None)

