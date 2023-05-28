"""
Modified from (C) 2011 Hanz Petrov <hanz.petrov@gmail.com>
MIDI Remote Script for generating Live API documentation,
"""

import Live
import os
from _Framework.ControlSurface import ControlSurface
import json
import inspect
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
            return f"{self.name}: {self.type}"
        else:
            return f"{self.name}: {self.type}={self.default}"

    def to_json(self):
        return {"name": self.name, "type": self.type, "default": self.default}


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

    def to_json(self):
        return {
            "name": self.name,
            "arguments": [x.to_json() for x in self.arguments],
            "return_type": self.return_type,
        }


def parse_arg(arg_string):
    arg_parts = arg_string.split("=")
    arg_parts = [part.replace("[", "").strip() for part in arg_parts]

    type_, name = arg_parts[0].split(")")
    type_ = type_.replace("(", "").strip()
    name = name.strip()

    if len(arg_parts) > 1:
        default = arg_parts[1]
    else:
        default = None

    if type_ == "object":
        type_ = "Any"

    return Argument(name, type_, default)


def parse_docstring(name: str, docstring: str):
    """Get the signature and return type from a docstring"""
    try:
        # get first line of docstring, and then remove ' :' from the end
        signature = docstring.split("\n")[0][:-2]
        # split into name with args and return type
        name_with_args, return_type = (x.strip() for x in signature.split("->"))
        # split function_name( (type)name, ...) and just get '(type)name, ...'
        args_string = name_with_args.split("( ")[1][:-1]
        # get individual non-optional args
        args = [parse_arg(x) for x in args_string.split(", ")]
        return FunctionSignature(name, args, return_type).to_json()
    except Exception as e:
        logger.exception("Failed to parse docstring for %s", name)
        return "<no signature available>"


# Create logger
logger = logging.getLogger("introspection")
logger.setLevel(logging.DEBUG)

# Create file handler
home_dir = os.path.expanduser("~")
fh = logging.FileHandler(os.path.join(home_dir, "logs.txt"))
fh.setLevel(logging.DEBUG)

# Create formatter and add it to the handler
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)

# Add handler to the logger
logger.addHandler(fh)


def introspect_module(module):
    logger.debug("Introspecting module: %s", module.__name__)
    try:
        module_info = {
            "name": module.__name__,
            "doc": inspect.getdoc(module),
            "members": {},
            "type": "module",
        }

        for name, obj in (
            (name, obj)
            for name, obj in inspect.getmembers(module)
            if not name.startswith("__")
        ):
            if inspect.ismodule(obj):
                module_info["members"][name] = introspect_module(obj)
            elif inspect.isclass(obj):
                module_info["members"][name] = introspect_class(obj)
            elif inspect.isfunction(obj) or inspect.isbuiltin(obj):
                module_info["members"][name] = introspect_function(obj)
            else:
                module_info["members"][name] = str(obj)
        return module_info
    except Exception as e:
        logger.exception("Failed to introspect module: %s", module.__name__)
        raise e


def get_function_signature(func):
    try:
        return str(inspect.signature(func))
    except ValueError:
        return "<no signature available>"


def get_text_signature(func):
    try:
        return func.__text_signature__
    except:
        return "<no signature available>"


def introspect_function(func):
    logger.debug("Introspecting function: %s", func.__name__)
    try:
        return {
            "name": func.__name__,
            "doc": inspect.getdoc(func),
            "type": "function",
            "signature": get_function_signature(func),
            "scraped_signature": parse_docstring(
                func.__name__, inspect.getdoc(func) or ""
            ),
        }
    except Exception as e:
        logger.exception("Failed to introspect function: %s", func.__name__)
        raise


def introspect_class(cls):
    logger.debug("Introspecting class: %s", cls.__name__)
    try:
        class_info = {
            "name": cls.__name__,
            "doc": inspect.getdoc(cls),
            "type": "class",
            "methods": {},
            "properties": {},
            "fields": {},
            "superclasses": [
                base.__name__ for base in cls.__bases__ if base.__name__ != "instance"
            ],
            "enum": None,
        }
        if "enum" in class_info["superclasses"]:
            enums = sorted(zip(cls.names, cls.values), key=lambda x: x[1])
            class_info["enum"] = list(
                sorted(((k, v) for k, v in enums), key=lambda x: x[1])
            )
        super_attrs = set()
        for base in cls.__bases__:
            for attr in base.__dict__:
                super_attrs.add(attr)
        logger.info("super_attrs: %s", super_attrs)

        # name: introspect_function(method) for name, method in inspect.getmembers(cls, inspect.isroutine) if not name.startswith('__')
        for name, obj in inspect.getmembers(cls):
            if name in super_attrs:
                continue
            if inspect.isroutine(obj) and not name.startswith("__"):
                class_info["methods"][name] = introspect_function(obj)
            elif inspect.isdatadescriptor(obj) and not name.startswith("__"):
                class_info["properties"][name] = obj.__doc__
            elif not (
                name.startswith("__") and name.endswith("__")
            ):  # Exclude special methods
                class_info["fields"][name] = (
                    type(obj).__name__ if type(obj).__name__ != "class" else "type"
                )

        return class_info
    except Exception as e:
        logger.exception("Failed to introspect class: %s", cls.__name__)
        raise e


class AAPIStub(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        module = Live

        outfilename = str(module.__name__) + ".json"
        outfilename = os.path.join(os.path.expanduser("~"), outfilename)
        with open(outfilename, "w") as f:
            f.write(json.dumps(introspect_module(module), indent=2))

    def disconnect(self):
        ControlSurface.disconnect(self)
