from typing import TypedDict, Optional, Literal, Union, Tuple, cast
from gen.DictTypes import *
import json
import file_helpers

INDENT = "    "
ANY = "from typing import Any"

hierarchy_class_lookups: dict[str, list[str]] = {}


def preprocess_classes(module: Module, hierarchy: list[str] = []) -> None:
    classes = [x for x in module["members"].values() if x["type"] == "class"]
    for class_ in classes:
        hierarchy_class_lookups[class_["name"]] = hierarchy
    modules = [x for x in module["members"].values() if x["type"] == "module"]
    for module_ in modules:
        preprocess_classes(cast(Module, module_), hierarchy + [module_["name"]])


def generate_imports(names: list[str]) -> str:
    names = sanitize_importable_types(names)
    imports = []
    for name in names:
        hierarchy = hierarchy_class_lookups[name]
        imports.append(f'from Live.{".".join(hierarchy)} import {name}')
    return "\n" + "\n".join(imports)


def generate_imports_from_functions(class_name: str, functions: list[Function]) -> str:
    names = []
    for function in functions:
        if isinstance(function["scraped_signature"], str):
            continue
        for arg in function["scraped_signature"]["arguments"]:
            names.append(arg["type"])
        names.append(function["scraped_signature"]["return_type"])

    sanitized_names = sanitize_importable_types(names)
    return generate_imports(sanitized_names)


def sanitize_importable_types(names: list[str]) -> list[str]:
    return list(set(name for name in names if name in hierarchy_class_lookups))


def indent(text: str, level: int = 1) -> str:
    return "\n".join(INDENT * level + line for line in text.split("\n"))


def arg_to_pyi(arg: Argument) -> str:
    if arg.get("default") is not None:
        default = f" = {arg['default']}"
    else:
        default = ""
    return f"{arg['name']}: {arg['type']}{default}"


def generate_function_pyi(function: Function, class_context: bool) -> str:
    # TODO: will need to "quote" the arg type if it is the class being defined
    scraped_signature = function["scraped_signature"]
    if isinstance(scraped_signature, str):
        return ""

    arguments = ", ".join(arg_to_pyi(arg) for arg in scraped_signature["arguments"])
    return_type = function["scraped_signature"]["return_type"]

    return indent(
        f'''
def {function['name']}({arguments}) -> {return_type}:
    """{function['doc']}"""
    ...''',
        level=1 if class_context else 0,
    )


def generate_property(prop: Property) -> str:
    name = prop["name"]
    docstring = prop["doc"]
    has_setter = prop["has_setter"]
    has_deleter = prop["has_deleter"]
    base = f'''
@property
def {name}(self):
    """{docstring}"""
    ...
'''
    if has_setter:
        base += f"""
@{name}.setter
def {name}(self, value):
    ...
"""
    if has_deleter:
        base += f"""
@{name}.deleter
def {name}(self):
    ...
"""
    return base


def generate_class_pyi(class_obj: Class) -> str:
    class_name = class_obj["name"]
    base_classes = ", ".join(class_obj["superclasses"])
    imports = "\n".join(["import enum", ANY, "from LomObject import LomObject"])
    imports += generate_imports_from_functions(
        class_name, cast(list[Function], class_obj["methods"].values())
    )
    imports += generate_imports(class_obj["superclasses"])

    methods = "\n".join(
        generate_function_pyi(method, True) for method in class_obj["methods"].values()
    )

    properties = "\n".join(
        indent(generate_property(prop))
        for name, prop in class_obj["properties"].items()
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
        class_def = f'''

{imports}

class {class_name}(enum.Enum):
    """{class_obj["doc"]}"""

{enum_values}
'''
    else:
        class_def = f'''
{imports}

class {class_name}({base_classes}):
    """{class_obj["doc"]}"""
    
{fields}
'''

    pyi_contents = f"""
{class_def}

{properties}

{methods}
    pass
"""

    return pyi_contents


def generate_module_pyi(module: Module, hierarchy: list[str] = []) -> str:
    docstring = module["doc"]
    members = module["members"]

    # imports = "\n".join(
    #     f"from {module_name} import {member['name']}" for member in members.values()
    # )

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
        process_module(module, hierarchy + [module["name"]])

    classes = [cast(Class, x) for x in members.values() if x["type"] == "class"]
    for class_obj in classes:
        process_class(class_obj, hierarchy)

    imports = "\n".join(f"from .{c['name']} import {c['name']}" for c in classes)

    pyi_contents = f'''"""{docstring}"""

{imports}

{functions}
'''

    return pyi_contents


def process_class(class_obj: Class, hierarchy: list[str] = []) -> None:
    print("class hierarchy:", hierarchy)

    pyi_contents = generate_class_pyi(class_obj)
    subpath = "/".join(hierarchy)
    path = f"Live/{subpath}"
    fname = f'{class_obj["name"]}.pyi'
    file_helpers.create_file(path, fname)
    with open(f"{path}/{fname}", "w") as file:
        file.write(pyi_contents)


def process_module(module: Module, hierarchy: list[str] = []) -> None:
    print("module hierarchy:", hierarchy)
    pyi_contents = generate_module_pyi(module, hierarchy)
    subpath = "/".join(hierarchy)
    path = f"Live/{subpath}"
    fname = f"__init__.pyi"
    file_helpers.create_file(path, fname)
    with open(f"{path}/{fname}", "w") as file:
        file.write(pyi_contents)


def process(module: Module) -> None:
    preprocess_classes(module)
    process_module(module)


with open("Live.json", "r") as file:
    json_data = json.load(file)

process(json_data)
