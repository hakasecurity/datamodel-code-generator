"""Strawberry GraphQL Input implementation.

This module inherits from Strawberry's BaseModel and only overrides the input-specific
attributes:

1. Uses @strawberry.input decorator instead of @strawberry.type
2. Uses strawberry/Input.jinja2 template  
3. Adds IMPORT_STRAWBERRY_INPUT instead of IMPORT_STRAWBERRY_TYPE

All other behavior (imports filtering, base class handling, DEFAULT_IMPORTS)
is inherited from BaseModel, eliminating code duplication.
"""
from __future__ import annotations

from datamodel_code_generator.model.strawberry.base_model import BaseModel
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_INPUT


class Input(BaseModel):
    """Strawberry GraphQL input type model.

    Generates @strawberry.input decorated classes for GraphQL input objects.
    Inherits all shared logic from BaseModel.
    """
    TEMPLATE_FILE_PATH: str = "strawberry/Input.jinja2"
    DECORATOR: str = "@strawberry.input"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace @strawberry.type import with @strawberry.input import
        self._additional_imports = [
            imp for imp in self._additional_imports 
            if imp.import_ != 'type' or imp.from_ != 'strawberry'
        ]
        self._additional_imports.append(IMPORT_STRAWBERRY_INPUT)
