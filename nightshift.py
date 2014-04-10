#!/usr/bin/env python3
# -*- python -*-
copyright='''
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

import os
import sys
import threading
from subprocess import Popen, PIPE


PROGRAM_NAME = 'nightshift'
PROGRAM_VERSION = '1.0'


for arg in sys.argv[1:]:
    if arg in ('-v', '--version'):
        print('%s %s' % (PROGRAM_NAME, PROGRAM_VERSION))
        Popen(['redshift', '-V'], stdout = sys.stdout).wait()
        sys.exit(0)
    elif arg in ('-c', '--copyright'):
        print(copyright[1 : -1])
        sys.exit(0)
    elif arg in ('-w', '--warranty'):
        print(copyright.split('\n\n')[-2])
        sys.exit(0)
    elif arg in ('-h', '--help'):
        text = '''USAGE: nightshift
                  
                  terminal user interface for redshift, a program for
                  setting the colour temperature of the display according
                  to the time of day.
                  
                    -h --help        Display this help message
                    -v --version     Show program version
                    -c --copyright   Show program copyright information
                    -w --warranty    Show program warrantly disclaimer
                  
                  Please report bugs to
                  <https://github.com/maandree/nightshift/issues>
               '''
        text = text.split('\n')[:-1]
        indent = min([len(line) - len(line.lstrip()) for line in text if line.rstrip().startswith(' ')])
        print('\n'.join([line[indent:] if line.startswith(' ') else line for line in text]))
        sys.exit(0)
    else:
        sys.stderr.write('%s: error: unrecognised option: %s\n' % (sys.argv[0], arg))
        sys.exit(1)

proc = Popen(['redshift', '-v'], stdout = PIPE, stderr = open(os.devnull))
red_brightness, red_period, red_temperature, red_running = 1, 1, 6500, True
red_condition = threading.Condition()

def read_status():
    global red_brightness, red_period, red_temperature, red_running
    while True:
        got = proc.stdout.readline()
        if (got is None) or (len(got) == 0):
            break
        got = got.decode('utf-8', 'replace')[:-1]
        (key, value) = got.split(': ')
        red_condition.acquire()
        try:
            if key == 'Brightness':
                red_brightness = float(value)
            elif key == 'Period':
                if value == 'Night':
                    red_period = 0
                elif value == 'Daytime':
                    red_period = 1
                else:
                    red_period = float(value.split(' ')[1][1 : -1]) / 100
            elif key == 'Color temperature':
                red_temperature = float(value[:-1])
        except:
            pass
        red_condition.notify()
        red_condition.release()
    red_running = False

thread = threading.Thread(target = read_status)
thread.setDaemon(True)
thread.start()


while red_running:
    red_condition.acquire()
    red_condition.wait()
    print('%f: %f, %f' % (red_period, red_temperature, red_brightness))
    red_condition.release()

