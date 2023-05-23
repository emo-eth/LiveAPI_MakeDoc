# http://remotescripts.blogspot.com

"""
Copyright (C) 2011 Hanz Petrov <hanz.petrov@gmail.com>
MIDI Remote Script for generating Live API documentation,
based on realtime inspection of the Live module.
Writes two files to the userhome directory - Live.xml and Live.css.

Inspired in part by the following Live API exploration modules:
dumpXML by Nathan Ramella http://code.google.com/p/liveapi/source/browse/trunk/docs/Ableton+Live+API/makedocs
and LiveAPIGen by Patrick Mueller http://muellerware.org

Parts of the describe methods are based on "describe" by Anand, found at:
http://code.activestate.com/recipes/553262-list-classes-methods-and-functions-in-a-module/

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
"""

import Live
import os, sys, types
from _Framework.ControlSurface import ControlSurface
import json
import inspect
import pprint
import logging
import os
from typing import Optional, List

class Argument:
    name: str
    type: str
    default: Optional[str]

    def __init__(self, name: str, type: str, default: Optional[str] = None):
        self.name = name
        self.type = type
        self.default = default

    def __str__(self):
        if self.default is None:
            return f'{self.name}: {self.type}'
        else:
            return f'{self.name}: {self.type}={self.default}'

class FunctionSignature:
    name: str
    arguments: List[Argument]
    return_type: str

    def __init__(self, name: str, arguments: List[Argument], return_type: str):
        self.name = name
        self.arguments = arguments
        self.return_type = return_type

    def __str__(self):
        return f'{self.name}({", ".join(str(x) for x in self.arguments)}) -> {self.return_type}'

def parse_arg(arg_string):
    arg_parts = arg_string.split('=')
    arg_parts = [part.replace('[', '').strip() for part in arg_parts]

    type_, name = arg_parts[0].split(')')
    type_ = type_.replace('(', '').strip()
    name = name.strip()

    if len(arg_parts) > 1:
        default = arg_parts[1]
    else:
        default = None

    return Argument(name, type_, default)



def parse_docstring(name:str, docstring: str):
    '''Get the signature and return type from a docstring'''
    try:
        # get first line of docstring, and then remove ' :' from the end
        signature = docstring.split('\n')[0][:-2]
        # split into name with args and return type
        name_with_args, return_type = (x.strip() for x in signature.split('->'))
        # split function_name( (type)name, ...) and just get '(type)name, ...'
        args_string = name_with_args.split('( ')[1][:-1]   
        # get individual non-optional args
        args = [parse_arg(x) for x in args_string.split(', ')]
        return str(FunctionSignature(name, args, return_type))
    except Exception as e:
        logger.exception('Failed to parse docstring for %s', name)
        return '<no signature available>'


# Create logger
logger = logging.getLogger('introspection')
logger.setLevel(logging.DEBUG)

# Create file handler
home_dir = os.path.expanduser("~")
fh = logging.FileHandler(os.path.join(home_dir, 'logs.txt'))
fh.setLevel(logging.DEBUG)

# Create formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

# Add handler to the logger
logger.addHandler(fh)

def introspect_module(module):
    logger.debug('Introspecting module: %s', module.__name__)
    try:
        module_info = {
            'name': module.__name__,
            'doc': inspect.getdoc(module),
            'members': {},
            
        }

        for name, obj in ((name, obj) for name, obj in inspect.getmembers(module) if not name.startswith('__')):
            if inspect.ismodule(obj):
                module_info['members'][name] = introspect_module(obj)
            elif inspect.isclass(obj):
                module_info['members'][name] = introspect_class(obj)
            elif inspect.isfunction(obj) or inspect.isbuiltin(obj):
                module_info['members'][name] = introspect_function(obj)
            else:
                module_info['members'][name] = str(obj)
        return module_info
    except Exception as e:
        logger.exception('Failed to introspect module: %s', module.__name__)
        raise e

def get_function_signature(func):
    try:
        return str(inspect.signature(func))
    except ValueError:
        return '<no signature available>'

def get_text_signature(func):
    try:
        return func.__text_signature__
    except:
        return '<no signature available>'

def introspect_function(func):
    logger.debug('Introspecting function: %s', func.__name__)
    try:
        return {
            'name': func.__name__,
            'doc': inspect.getdoc(func),
            'signature': get_function_signature(func),
            'scraped_signature': parse_docstring(func.__name__, inspect.getdoc(func) or ''),
            
        }
    except Exception as e:
        logger.exception('Failed to introspect function: %s', func.__name__)
        raise

def introspect_class(cls):
    logger.debug('Introspecting class: %s', cls.__name__)
    try:
        methods = {name: introspect_function(method) 
                    for name, method in cls.__dict__.items() 
                    if inspect.isroutine(method)}
        return {
            'name': cls.__name__,
            'doc': inspect.getdoc(cls),
            'methods': {name: introspect_function(method) for name, method in inspect.getmembers(cls, inspect.isroutine) if not name.startswith('__')},
        }
    except Exception as e:
        logger.exception('Failed to introspect class: %s', cls.__name__)
        raise e



class APIMakeDoc(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance) 
        module = Live
        
        outfilename = (str(module.__name__) + ".json")
        outfilename = (os.path.join(os.path.expanduser('~'), outfilename))
        # make_doc(module, outfilename)
        with open(outfilename, 'w') as f:
            f.write(json.dumps(introspect_module(module),indent=2))


    def disconnect(self):
        ControlSurface.disconnect(self)


# def make_doc(module, outfilename):
#     if outfilename != None:
#         stdout_old = sys.stdout

#         outputfile = open(outfilename, 'w')
#         sys.stdout = outputfile
#         print(generate_stub(module, 'Live'))
#         outputfile.close()
#         sys.stdout = stdout_old
            