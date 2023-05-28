from typing import TypedDict, Optional, Literal, Union, Tuple, cast
from gen.DictTypes import *
import json

INDENT = "    "
ANY = "from typing import Any"


def indent(text: str, level: int = 1) -> str:
    return "\n".join(INDENT * level + line for line in text.split("\n"))


def arg_to_pyi(arg: Argument) -> str:
    if arg.get("default") is not None:
        default = f" = {arg['default']}"
    else:
        default = ""
    return f"{arg['name']}: {arg['type']}{default}"


def generate_function_pyi(function: Function, class_context: bool) -> str:
    scraped_signature = function["scraped_signature"]
    if isinstance(scraped_signature, str):
        return ""
    print(function, scraped_signature)

    arguments = ", ".join(arg_to_pyi(arg) for arg in scraped_signature["arguments"])
    return_type = function["scraped_signature"]["return_type"]

    return indent(
        f"""
def {function['name']}({arguments}) -> {return_type}:
    '''{function['doc']}'''
    ...""",
        level=1 if class_context else 0,
    )


def generate_property(name: str, docstring: str) -> str:
    return f"""
@property
def {name}(self):
    '''{docstring}'''
    ...
"""


def generate_class_pyi(class_obj: Class) -> str:
    class_name = class_obj["name"]
    base_classes = ", ".join(class_obj["superclasses"])

    methods = "\n".join(
        generate_function_pyi(method, True) for method in class_obj["methods"].values()
    )

    properties = "\n".join(
        indent(generate_property(prop_name, prop_type))
        for prop_name, prop_type in class_obj["properties"].items()
    )

    fields = "\n".join(
        indent(f"{field_name}: {field_type}")
        for field_name, field_type in class_obj["fields"].items()
    )

    class_def = ""
    if class_obj["enum"]:
        enum_values = "\n".join(
            indent(f"{name} = {value}") for name, value in class_obj["enum"]
        )
        class_def = f"""
class {class_name}(enum.Enum):
{enum_values}
"""
    else:
        class_def = f"""class {class_name}({base_classes}):
{fields}
"""

    pyi_contents = f"""
{class_def}

{properties}

{methods}
"""

    return pyi_contents


def generate_module_pyi(module: Module) -> str:
    docstring = module["doc"]
    members = module["members"]

    # imports = "\n".join(
    #     f"from {module_name} import {member['name']}" for member in members.values()
    # )
    imports = "\n".join(["import enum", ANY, "from LomObject import LomObject"])

    classes = "\n\n".join(
        generate_class_pyi(cast(Class, class_obj))
        for class_obj in members.values()
        if class_obj["type"] == "class"
    )

    functions = "\n\n".join(
        generate_function_pyi(cast(Function, function), False)
        for function in members.values()
        if function["type"] == "function"
    )

    modules: list[Module] = [
        cast(Module, x) for x in members.values() if x["type"] == "module"
    ]
    for module in modules:
        process_module(module)

    pyi_contents = f"""'''{docstring}'''

{imports}

{classes}

{functions}
"""

    return pyi_contents


# Example usage:
json_data = {
    "name": "my_module",
    "doc": "This is my module.",
    "type": "module",
    "members": {
        "MyClass": {
            "name": "MyClass",
            "doc": "This is my class.",
            "type": "class",
            "methods": {
                "method1": {
                    "name": "method1",
                    "signature": "def method1(self, arg1: int, arg2: str) -> None",
                    "scraped_signature": {
                        "name": "method1",
                        "arguments": [
                            {"name": "self", "type": "MyClass"},
                            {"name": "arg1", "type": "int"},
                            {"name": "arg2", "type": "str"},
                        ],
                        "return_type": "None",
                    },
                }
            },
            "properties": {
                "prop1": "This is property 1.",
                "prop2": "This is property 2.",
            },
            "fields": {"field1": "str", "field2": "int"},
            "superclasses": ["object"],
            "enum": None,
        },
        "my_function": {
            "name": "my_function",
            "doc": "This is my function.",
            "type": "function",
            "signature": "def my_function(arg: int) -> str",
            "scraped_signature": {
                "name": "my_function",
                "arguments": [{"name": "arg", "type": "int"}],
                "return_type": "str",
            },
        },
    },
}


def process_module(module: Module) -> None:
    pyi_contents = generate_module_pyi(module)
    with open(f"out/{module['name']}.pyi", "w") as file:
        file.write(pyi_contents)


with open("Live.json", "r") as file:
    json_data = json.load(file)

process_module(json_data)
