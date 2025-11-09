"""Strawberry GraphQL Enum implementation.

This module inherits from the base Enum class while customizing only the output format,
and overrides only the enum-specific behaviors needed for Strawberry:

1. Uses @strawberry.enum decorator
2. Uses strawberry/Enum.jinja2 template
3. Adds strawberry.enum import

The base Enum class provides all enum parsing logic, eliminating the need
for duplicate enum handling code in a separate Strawberry parser.
"""
from __future__ import annotations

from datamodel_code_generator.model.enum import Enum as _Enum
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_ENUM
from datamodel_code_generator.model.base import BaseClassDataType
from datamodel_code_generator.imports import Import


class Enum(_Enum):
    """Strawberry GraphQL enum model.

    Generates @strawberry.enum decorated Python Enum classes.
    """
    TEMPLATE_FILE_PATH: str = "strawberry/Enum.jinja2"
    BASE_CLASS: str = "Enum"
    DECORATOR: str = "@strawberry.enum"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._additional_imports.append(IMPORT_STRAWBERRY_ENUM)

    def set_base_class(self) -> None:
        """Override to use Enum as base class without importing it."""
        # For Strawberry enums, we need Enum as base class
        enum_import = Import(import_="Enum", alias="Enum", from_="enum")
        self.base_classes = [BaseClassDataType.from_import(enum_import)]
