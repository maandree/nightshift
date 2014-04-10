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
import socket
import threading
from subprocess import Popen, PIPE


PROGRAM_NAME = 'nightshift'
'''
:str  The name of the program
'''

PROGRAM_VERSION = '1.0'
'''
:str  The version of the program
'''


## Set process title
def setproctitle(title):
    '''
    Set process title
    
    @param  title:str  The title of the process
    '''
    import ctypes
    try:
        # Remove path, keep only the file,
        # otherwise we get really bad effects, namely
        # the name title is truncates by the number
        # of slashes in the title. At least that is
        # the observed behaviour when using procps-ng.
        title = title.split('/')[-1]
        # Create strng buffer with title
        title = title.encode(sys.getdefaultencoding(), 'replace')
        title = ctypes.create_string_buffer(title)
        if 'linux' in sys.platform:
            # Set process title on Linux
            libc = ctypes.cdll.LoadLibrary('libc.so.6')
            libc.prctl(15, ctypes.byref(title), 0, 0, 0)
        elif 'bsd' in sys.platform:
            # Set process title on at least FreeBSD
            libc = ctypes.cdll.LoadLibrary('libc.so.7')
            libc.setproctitle(ctypes.create_string_buffer(b'-%s'), title)
    except:
        pass
setproctitle(sys.argv[0])


red_args = None
'''
:list<str>?  Raw arguments passed to redshift
'''

red_opts = []
'''
:list<str>  Nightshift parsed options passed to redshift
'''

daemon = False
'''
:bool  Whether or not to run as daemon
'''

kill = False
'''
:bool  Whether or not to kill the redshift and the nightshift daemon
'''

toggle = False
'''
:bool  Whether or not to toggle redshift
'''

status = False
'''
:bool  Whether or not to get the current status
'''


## Parse options
add_to_red_opts = False
for arg in sys.argv[1:]:
    if add_to_red_opts:
        red_opts.append(arg)
        add_to_red_opts = False
    elif red_args is not None:
        red_args.append(arg)
    elif arg in ('-V', '--version', '-version'):
        ## Print the version of nightshift and of redshift
        print('%s %s' % (PROGRAM_NAME, PROGRAM_VERSION))
        Popen(['redshift', '-V'], stdout = sys.stdout).wait()
        sys.exit(0)
    elif arg in ('-C', '--copyright', '-copyright'):
        ## Print copyright information
        print(copyright[1 : -1])
        sys.exit(0)
    elif arg in ('-W', '--warranty', '-warranty'):
        ## Print warranty disclaimer
        print(copyright.split('\n\n')[-2])
        sys.exit(0)
    elif arg in ('-h', '-?', '--help', '-help'):
        ## Display help message
        text = '''USAGE: nightshift [OPTIONS...] [-- REDSHIFT-OPTIONS...]
                  
                  Terminal user interface for redshift, a program for setting the colour
                  temperature of the display according to the time of day.
                  
                    -h --help                       Display this help message
                    -V --version                    Show program version
                    -C --copyright                  Show program copyright information
                    -W --warranty                   Show program warrantly disclaimer
                    
                    -d --daemon                     Start as daemon
                    -x --reset --kill               Remove adjustment from screen
                    +x --toggle                     Temporarily disable or enable adjustments
                    -s --status                     Print status information
                    
                    -c --config         FILE        Load settings from specified configuration file
                    -b --brightness     DAY:NIGHT   Screen brightness to set at daytime/night
                    -b --brightness     BRIGHTNESS  Screen brightness to apply
                    -t --temperature    DAY:NIGHT   Colour temperature to set at daytime/night
                    -t --temperature    TEMP        Colour temperature to apply
                    -l --location       LAT:LON     Your current location
                    -l --location       PROVIDER    Select provider for automatic location updates
                                                    (Type `list' to see available providers)
                    -m --method         METHOD      Method to use to set colour temperature
                                                    (Type `list' to see available methods)
                    -r --no-transition              Disable temperature transitions
                  
                  Please report bugs to <https://github.com/maandree/nightshift/issues>
               '''
        text = text.split('\n')[:-1]
        indent = min([len(line) - len(line.lstrip()) for line in text if line.rstrip().startswith(' ')])
        print('\n'.join([line[indent:] if line.startswith(' ') else line for line in text]))
        sys.exit(0)
    elif arg == '--':
        red_args = []
    else:
        subargs = [arg]
        if arg.startswith('-') and not arg.startswith('--'):
            subargs = ['-' + letter for letter in arg[1:]]
        elif arg.startswith('+') and not arg.startswith('++'):
            subargs = ['+' + letter for letter in arg[1:]]
        red_arg = ''
        for arg in subargs:
            if (add_to_red_opts is None) or add_to_red_opts:
                add_to_red_opts = None
                red_arg += arg[1]
            elif arg in ('-d', '--daemon'):
                daemon = True
            elif arg in ('-x', '--reset', '--kill'):
                kill = True
            elif arg in ('+x', '--toggle'):
                toggle = True
            elif arg in ('-s', '--status'):
                status = True
            elif arg in ('-c', '--config'):
                red_opts.append('-c')
                add_to_red_opts = True
            elif arg in ('-b', '--brightness'):
                red_opts.append('-b')
                add_to_red_opts = True
            elif arg in ('-t', '--temperature'):
                red_opts.append('-t')
                add_to_red_opts = True
            elif arg in ('-l', '--location'):
                red_opts.append('-l')
                add_to_red_opts = True
            elif arg in ('-m', '--method'):
                red_opts.append('-m')
                add_to_red_opts = True
            elif arg in ('-r', '--no-transition'):
                red_opts.append('-r')
                add_to_red_opts = True
            else:
                ## Unrecognised option
                sys.stderr.write('%s: error: unrecognised option: %s\n' % (sys.argv[0], arg))
                sys.exit(1)
        if add_to_red_opts is None:
            red_opts.append(red_arg)
            add_to_red_opts = False


# Construct name of socket
socket_path = '%s.%s~%s' % ('/dev/shm/', PROGRAM_NAME, os.environ['USER'])
# Create socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    # Connect to the server
    sock.connect(socket_path)
except:
    # The process need separate sockets, lets close it
    # and let both process recreate it
    sock.close()
    sock = None

if sock is None:
    ## Server is not running
    # Create pipe for interprocess signal
    (r_end, w_end) = os.pipe()
    
    # Duplicate process.
    pid = os.fork()
    
    if pid == 0:
        ## Daemon (child)
        # Close stdin and stdout
        os.close(sys.stdin.fileno())
        os.close(sys.stdout.fileno())
        
        # Create server socket
        os.unlink(socket_path)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(socket_path)
        sock.listen(5)
        
        # Send signal
        with os.fdopen(w_end, 'wb') as file:
            file.write(b'\n')
            file.flush()
        
        # Close the pipe
        os.close(r_end)
        
        ## TODO (for testing)
        import signal
        while True:
            signal.pause()
        
        # Close socket
        sock.close()
        # Close process
        sys.exit(0)
    else:
        ## Front-end (parent)
        # Wait for a signal
        rc = None
        with os.fdopen(r_end, 'rb') as file:
            file.read(1)
        
        # Close the pipe
        os.close(w_end)
        
        # Connect to the server
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        print('connecting')
        sock.connect(socket_path)
        print('connected')


try:
    proc = Popen(['redshift', '-v'], stdout = PIPE, stderr = open(os.devnull))
    red_brightness, red_period, red_temperature, red_running, red_status = 1, 1, 6500, True, True
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
                else key == 'Status':
                    red_status = value == 'Enabled'
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

finally:
    # Close socket
    sock.close()

