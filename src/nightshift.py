#!/usr/bin/env python3
# -*- python -*-
copyright='''
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

import os
import sys
import socket
import signal
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


backlog = 5
'''
:int  The size of the server socket's backlog
'''

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

conf_opts = []
'''
:list<str>  This list will always have at least one element. This list is filled
            with options passed to the configurations, with the first element
            being the configuration file
'''

config_file = None
'''
:str?  The configuration file, same as the first element in `conf_opts`
'''


## Parse options
add_to_red_opts = False
reading_conf_opts = False
for arg in sys.argv[1:]:
    if add_to_red_opts:
        red_opts.append(arg)
        add_to_red_opts = False
    elif reading_conf_opts:
        if arg == '}':
            reading_conf_opts = False
        else:
            conf_opts.append(arg)
    elif isinstance(config_file, list):
        config_file = arg
    elif red_args is not None:
        red_args.append(arg)
    elif arg == '{':
        reading_conf_opts = True
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
        text = '''USAGE: nightshift [OPTIONS...] ['{' SCRIPT-OPTIONS... '}'] ['--' REDSHIFT-OPTIONS...]
                  
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
                    +c --script         FILE        Load nightshift configuration script from specified file
                    
                    -c --config         FILE        Load redshift settings from specified file
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
            elif isinstance(config_file, list):
                config_file.append(arg[1])
            elif arg in ('-d', '--daemon'):             daemon = True
            elif arg in ('-x', '--reset', '--kill'):    kill += 1
            elif arg in ('+x', '--toggle'):             toggle = True
            elif arg in ('-s', '--status'):             status = True
            elif arg in ('+c', '--script'):             config_file = []
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
        if isinstance(config_file, list):
            config_file = ''.join(config_file)


# Parse help request for -l and -m
for opt in ('-l', '-m'):
    i = 0
    while opt in red_opts[i:]:
        i = red_opts.index(opt) + 1
        if not i == len(red_opts):
            arg = red_opts[i]
            if (arg == 'list') or ('help' in arg.split(':')):
                proc = ['redshift', opt, arg]
                proc = Popen(proc, stdout = sys.stdout, stderr = sys.stderr)
                proc.wait()
                sys.exit(proc.returncode)
# Translate single-parameter -t into dual-parameter -t
i = 0
while '-t' in red_opts[i:]:
    i = red_opts.index('-t') + 1
    if not i == len(red_opts):
        if ':' not in red_opts[i]:
            red_opts[i] = '%s:%s' % (red_opts[i], red_opts[i])



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


def read_status(proc, sock):
    '''
    Read status from redshift
    
    @param  proc:Popen   The redshift process
    @param  sock:socket  The server socket
    '''
    global red_brightness, red_temperature
    global red_brightnesses, red_temperatures
    global red_period, red_location
    global red_status, red_running
    released = True
    while True:
        got = proc.stdout.readline()
        if (got is None) or (len(got) == 0):
            break
        got = got.decode('utf-8', 'replace')[:-1]
        (key, value) = got.split(': ')
        if released:
            red_condition.acquire()
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
                # Neither version is followed by anything, notify and release
                released = True
            elif key == 'Status':
                red_status = value == 'Enabled'
                # Not followed by anything, notify and release
                released = True
            if released:
                red_condition.notify_all()
                red_condition.release()
        except:
            pass
    if released:
        red_condition.acquire()
    red_running = False
    red_condition.notify_all()
    red_condition.release()
    sock.shutdown(socket.SHUT_RDWR)


def use_client(sock, proc):
    '''
    Communication with client
    
    @param  sock:socket  The socket connected to the client
    @param  proc:Popen   The redshift process
    '''
    buf = ''
    closed = False
    while not closed:
        got = sock.recv(128).decode('utf-8', 'error')
        if (got is None) or (len(got) == 0):
            break
        buf += got
        while '\n' in buf:
            buf = buf.split('\n')
            message, buf = buf[0], '\n'.join(buf[1:])
            if message == 'status':
                red_condition.acquire()
                message =  'Current brightness: %f\n' % red_brightness
                message += 'Daytime brightness: %f\n' % red_brightnesses[0]
                message += 'Night brightness: %f\n' % red_brightnesses[1]
                message += 'Current temperature: %f\n' % red_temperature
                message += 'Daytime temperature: %f\n' % red_temperatures[0]
                message += 'Night temperature: %f\n' % red_temperatures[1]
                message += 'Dayness: %f\n' % red_period
                message += 'Latitude: %f\n' % red_location[0]
                message += 'Longitude: %f\n' % red_location[1]
                message += 'Enabled: %s\n' % ('yes' if red_status else 'no')
                message += 'Running: %s\n' % ('yes' if red_running else 'no')
                sock.sendall(message.encode('utf-8'))
                red_condition.release()
            elif message == 'toggle':
                proc.send_signal(signal.SIGUSR1)
            elif message == 'kill':
                proc.terminate()
            elif message == 'close':
                closed = True
            elif message == 'listen':
                pass ## TODO
    sock.close()


def run_as_daemon(sock):
    '''
    Perform daemon logic
    
    @param  sock:socket  The server socket
    '''
    global red_condition, red_pid
    
    # Create status condition
    red_condition = threading.Condition()
    
    # Start redshift
    command = ['redshift'] + red_opts
    if red_args is not None:
        command += red_args
    proc = Popen(command, stdout = PIPE, stderr = open(os.devnull))
    
    # Read status from redshift
    thread = threading.Thread(target = read_status, args = (proc, sock))
    thread.setDaemon(True)
    thread.start()
    
    red_condition.acquire()
    while red_running:
        red_condition.release()
        try:
            (client_sock, _client_address) = sock.accept()
        except:
            pass # We have shut down the socket so that accept halts
        client_thread = threading.Thread(target = use_client, args = (client_sock, proc))
        client_thread.setDaemon(True)
        client_thread.start()
        red_condition.acquire()
    
    red_condition.release()
    thread.join()


def do_daemon():
    '''
    Run actions for --daemon
    '''
    if (kill > 0) or toggle or status:
        print('%s: error: -x, +x and -s can be used when running as the daemon' % sys.argv[0])
        sys.exit(1)
    
    # Create server socket
    try:
        os.unlink(socket_path)
    except:
        pass # The fill does (probably) not exist
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_path)
    sock.listen(backlog)
    
    # Perform daemon logic
    run_as_daemon(sock)
    
    # Close socket
    sock.close()


def not_running():
    '''
    Run actions for --status when the daemon is not running
    '''
    print('Not running')


def do_status():
    '''
    Run actions for --status when the daemon is running
    '''
    sock.sendall('status\n'.encode('utf-8'))
    while True:
        got = sock.recv(1024)
        if (got is None) or (len(got) == 0):
            break
        sys.stdout.buffer.write(got)
        sys.stdout.buffer.flush()


def do_toggle():
    '''
    Run actions for --toggle
    '''
    sock.sendall('toggle\n'.encode('utf-8'))


def do_kill():
    '''
    Run actions for --kill
    '''
    sock.sendall('kill\n'.encode('utf-8'))
    if kill > 1:
        sock.sendall('kill\n'.encode('utf-8'))


def create_daemon():
    '''
    Start daemon when it is required but is not running
    '''
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
        try:
            os.unlink(socket_path)
        except:
            pass # The fill does (probably) not exist
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(socket_path)
        sock.listen(backlog)
        
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


def create_client():
    '''
    Create client socket and start daemon if not running
    
    @return  :socket  The client socket
    '''
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
            not_running()
            sys.exit(0)
    
    if sock is None:
        # Create daemon and wait for it to start listening for clients
        create_daemon()
        
        # Connect to the server
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
    
    return sock


def run_as_client():
    '''
    Perform client actions
    '''
    # Temporarily disable or enable redshift
    if toggle:
        do_toggle()
        sock.sendall('close\n'.encode('utf-8'))
    
    # Kill redshift and the night daemon
    if kill > 0:
        do_kill()
    
    # Get redshift status
    if status:
        do_status()
        sock.close()
    
    # Start user interface
    if (kill == 0) and not (status or toggle):
        sock.sendall('listen\n'.encode('utf-8'))
        user_interface()


def do_client():
    '''
    Do everything that has to do with being a client
    '''
    global sock
    # Connect to client
    sock = create_client()
    
    # Perform client actions
    run_as_client()
    
    # Close socket
    sock.sendall('close\n'.encode('utf-8'))
    sock.close()


def run():
    '''
    Run as either the daemon (if --daemon) or as a client (otherwise)
    '''
    if daemon:
        do_daemon()
    else:
        do_client()


def user_interface():
    '''
    Start user interface
    '''
    pass # TODO


## Load extension and configurations via blueshiftrc
# No configuration script has been selected explicitly,
# so select one automatically.
if config_file is None:
    # Possible auto-selected configuration scripts,
    # earlier ones have precedence, we can only select one.
    files = []
    def add_files(var, *ps, multi = False):
        if var == '~':
            try:
                # Get the home (also known as initial) directory of the real user
                import pwd
                var = pwd.getpwuid(os.getuid()).pw_dir
            except:
                return
        else:
            # Resolve environment variable or use empty string if none is selected
            if (var is None) or (var in os.environ) and (not os.environ[var] == ''):
                var = '' if var is None else os.environ[var]
            else:
                return
        paths = [var]
        # Split environment variable value if it is a multi valeu variable
        if multi and os.pathsep in var:
            paths = [v for v in var.split(os.pathsep) if not v == '']
        # Add files according to patterns
        for p in ps:
            p = p.replace('/', os.sep).replace('%', PROGRAM_NAME)
            for v in paths:
                files.append(v + p)
    add_files('XDG_CONFIG_HOME', '/%/%rc', '/%rc')
    add_files('HOME',            '/.config/%/%rc', '/.%rc')
    add_files('~',               '/.config/%/%rc', '/.%rc')
    add_files('XDG_CONFIG_DIRS', '/%rc', multi = True)
    add_files(None,              '/etc/%rc')
    for file in files:
        # If the file we exists,
        if os.path.exists(file):
            # select it,
            config_file = file
            # and stop trying files with lower precedence.
            break
# As the zeroth argument for the configuration script,
# add the configurion script file. Just like the zeroth
# command line argument is the invoked command.
conf_opts = [config_file] + conf_opts
if config_file is not None:
    code = None
    # Read configuration script file
    with open(config_file, 'rb') as script:
        code = script.read()
    # Decode configurion script file and add a line break
    # at the end to ensure that the last line is empty.
    # If it is not, we will get errors.
    code = code.decode('utf-8', 'error') + '\n'
    # Compile the configuration script,
    code = compile(code, config_file, 'exec')
    # and run it, with it have the same
    # globals as this module, so that it can
    # not only use want we have defined, but
    # also redefine it for us.
    g, l = globals(), dict(locals())
    for key in l:
        g[key] = l[key]
    exec(code, g)


run()

