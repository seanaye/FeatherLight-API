"""import and define schem execution"""
from ariadne import (
    load_schema_from_path,
    make_executable_schema,
    snake_case_fallback_resolvers
)
from .types import TYPES as resolvers
from .directives import AuthDirective, RatelimitDirective

_TYPE_DEFS = load_schema_from_path('schema')

SCHEMA = make_executable_schema(
    _TYPE_DEFS,
    resolvers,
    snake_case_fallback_resolvers,
    directives={
        'auth': AuthDirective,
        'limit': RatelimitDirective
    }
)
