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

red_opts = ['-v']
'''
:list<str>  Nightshift parsed options passed to redshift
'''

daemon = False
'''
:bool  Whether or not to run as daemon
'''

kill = 0
'''
:int  Whether or not to kill the redshift and the nightshift daemon,
      0 for no, 1 for yes, 2 for immediately
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
        if   arg.startswith('-') and not arg.startswith('--'):  subargs = ['-' + letter for letter in arg[1:]]
        elif arg.startswith('+') and not arg.startswith('++'):  subargs = ['+' + letter for letter in arg[1:]]
        red_arg = ''
        for arg in subargs:
            if (add_to_red_opts is None) or add_to_red_opts:
                add_to_red_opts = None
                red_arg += arg[1]
            elif arg in ('-d', '--daemon'):             daemon = True
            elif arg in ('-x', '--reset', '--kill'):    kill += 1
            elif arg in ('+x', '--toggle'):             toggle = True
            elif arg in ('-s', '--status'):             status = True
            else:
                add_to_red_opts = True
                if   arg in ('-c', '--config'):         red_opts.append('-c')
                elif arg in ('-b', '--brightness'):     red_opts.append('-b')
                elif arg in ('-t', '--temperature'):    red_opts.append('-t')
                elif arg in ('-l', '--location'):       red_opts.append('-l')
                elif arg in ('-m', '--method'):         red_opts.append('-m')
                elif arg in ('-r', '--no-transition'):  red_opts.append('-r')
                else:
                    ## Unrecognised option
                    sys.stderr.write('%s: error: unrecognised option: %s\n' % (sys.argv[0], arg))
                    sys.exit(1)
        if add_to_red_opts is None:
            red_opts.append(red_arg)
            add_to_red_opts = False


# Construct name of socket
socket_path = '%s.%s~%s' % ('/dev/shm/', PROGRAM_NAME, os.environ['USER'])
'''
The pathname of the interprocess communication socket for nightshift
'''


# The status of redshift
red_brightness, red_temperature = 1, 6500
red_brightnesses, red_temperatures = (1, 1), (5500, 3600)
red_period, red_location = 1, (0, 0)
red_status, red_running = True, True
red_condition = None


def read_status(proc):
    '''
    Read status from redshift
    
    @param  proc:Popen  The redshift process
    '''
    global red_brightness, red_temperature
    global red_brightnesses, red_temperatures
    global red_period, red_location
    global red_status, red_running
    while True:
        got = proc.stdout.readline()
        if (got is None) or (len(got) == 0):
            break
        got = got.decode('utf-8', 'replace')[:-1]
        (key, value) = got.split(': ')
        red_condition.aquire()
        try:
            if key == 'Location':
                red_location = [float(v) for v in value.split(', ')]
                # Followed by 'Temperatures'
            elif key == 'Temperatures':
                red_temperatures = [float(v.split(' ')[0][:-1]) for v in value.split(', ')]
                # Followed by two parameter 'Brightness'
            elif key == 'Period':
                if value == 'Night':
                    red_period = 0
                elif value == 'Daytime':
                    red_period = 1
                else:
                    red_period = float(value.split(' ')[1][1 : -1]) / 100
                # Followed by 'Color temperature'
            elif key == 'Color temperature':
                red_temperature = float(value[:-1])
                # Followed by one parameter 'Brightness'
            elif key == 'Brightness':
                if ':' in value:
                    red_brightnesses = [float(v) for v in value.split(':')]
                else:
                    red_brightness = float(value)
                # Neither version is followed by anything, notify
                red_condition.notify_all()
            else key == 'Status':
                red_status = value == 'Enabled'
                # Not followed by anything, notify
                red_condition.notify_all()
        except:
            pass
        red_condition.release()
    red_condition.aquire()
    red_running = False
    red_condition.notify_all()
    red_condition.release()


def run_as_daemon(sock):
    '''
    Perform daemon logic
    
    @param  sock:socket  The server socket
    '''
    global red_condition
    
    # Create status condition
    red_condition = thread.Condition()
    
    # Start redshift
    command = ['redshift'] + red_opts
    if red_args is not None:
        command += red_args
    proc = Popen(command, stdout = PIPE, stderr = open(os.devnull))
    
    # Read status from redshift
    thread = threading.Thread(target = read_status)
    thread.setDaemon(True)
    thread.start()
    
    # TODO


if daemon:
    if (kill > 0) or toggle or status:
        print('%s: error: -x, +x and -s can be used when running as the daemon' % sys.argv[0])
        sys.exit(1)
    
    # Create server socket
    os.unlink(socket_path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_path)
    sock.listen(5)
    
    # Perform daemon logic
    run_as_daemon(sock)
    
    # Close socket
    sock.close()
    # Close process
    sys.exit(0)


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
    
    if status:
        print('Not running')
        sys.exit(0)

if sock is None:
    ## Server is not running
    # Create pipe for interprocess signal
    (r_end, w_end) = os.pipe()
    
    # Duplicate process
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
        
        # Perform daemon logic
        run_as_daemon(sock)
        
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
        sock.connect(socket_path)


# Get redshift status
if status:
    sock.sendall('status\n')
    while True:
        got = sock.recv(1024)
        if (got is None) or (len(got) == 0):
            break
        sys.stdout.buffer.write(got)
    sys.stdout.buffer.flush()

# Temporarily disable or enable redshift
if toggle:
    sock.sendall('toggle\n')

# Kill redshift and the night daemon
if kill >= 1:
    sock.sendall('kill\n')

# Kill redshift and the night daemon immediately
if kill >= 2:
    sock.sendall('kill\n')


# Start user interface
if (kill == 0) and not (status or toggle):
    sock.sendall('listen\n')
    pass # TODO


# Close socket
sock.close()

