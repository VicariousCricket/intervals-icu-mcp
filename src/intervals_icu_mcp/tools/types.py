"""Shared parameter types for MCP tools.

The MCP client (Claude Code) encodes all XML parameter values as strings before
sending them to the server. These types accept strings and coerce to the target
Python type so tools work correctly with explicitly passed values.
"""

from typing import Annotated, Any

from pydantic import BeforeValidator
from pydantic.json_schema import WithJsonSchema


def _to_int(v: Any) -> int:
    if isinstance(v, str):
        return int(v)
    return int(v)


def _to_optional_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    return _to_int(v)


# Use these in place of bare `int` / `int | None` in Annotated tool parameters.
# They accept numeric strings ("60") while keeping {type: integer} in the JSON schema.
IntParam = Annotated[
    int,
    BeforeValidator(_to_int),
    WithJsonSchema({"type": ["integer", "string"]}),
]

OptionalIntParam = Annotated[
    int | None,
    BeforeValidator(_to_optional_int),
    WithJsonSchema({"anyOf": [{"type": ["integer", "string"]}, {"type": "null"}]}),
]
