from typing import TypedDict, Optional, Literal, Union, Tuple

Name = str
EnumVal = Tuple[Name, int]
Type = str
Docstring = str


class Argument(TypedDict):
    name: str
    type: str
    default: Optional[str]


class FunctionSignature(TypedDict):
    name: str
    arguments: list[Argument]
    return_type: str


class BaseDict(TypedDict):
    name: str
    doc: str
    type: Union[Literal["function"], Literal["class"], Literal["module"]]


class Function(BaseDict):
    signature: str
    scraped_signature: FunctionSignature


class Class(BaseDict):
    methods: dict[Name, Function]
    properties: dict[Name, Docstring]
    fields: dict[Name, Type]
    superclasses: list[Name]
    enum: Optional[list[EnumVal]]


class Module(BaseDict):
    members: dict[str, BaseDict]
