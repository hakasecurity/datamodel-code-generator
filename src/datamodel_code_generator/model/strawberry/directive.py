"""Strawberry GraphQL Directive implementation.

This module inherits from PydanticBaseModel to reuse Pydantic's directive parsing
while customizing only the output format, and overrides only the directive-specific behaviors needed for Strawberry, 
and adding directive-specific features:

1. Uses @strawberry.schema_directive decorator
2. Handles directive locations (e.g., FIELD_DEFINITION, INPUT_FIELD_DEFINITION)
3. Uses strawberry/Directive.jinja2 template
4. Overrides DEFAULT_IMPORTS to prevent Pydantic-specific imports

This enables Strawberry to reuse all of Pydantic's directive parsing logic while
generating Strawberry-specific directive syntax.
"""
from __future__ import annotations

from datamodel_code_generator.model.pydantic.base_model import BaseModel as PydanticBaseModel
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_DIRECTIVE, IMPORT_STRAWBERRY_LOCATION


class Directive(PydanticBaseModel):
    """Strawberry GraphQL directive model.

    Generates @strawberry.schema_directive decorated classes for GraphQL directives.
    """
    TEMPLATE_FILE_PATH: str = "strawberry/Directive.jinja2"
    BASE_CLASS: str = "object"
    DECORATOR: str = "@strawberry.schema_directive"
    DEFAULT_IMPORTS: tuple = ()  # Override to remove pydantic imports

    def __init__(self, *args, locations=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._additional_imports.append(IMPORT_STRAWBERRY_DIRECTIVE)
        self.locations = locations or []
        if self.locations:
            self._additional_imports.append(IMPORT_STRAWBERRY_LOCATION)

    def set_base_class(self) -> None:
        """Override to not import built-in Python types."""
        # For Strawberry directives, we don't need to import object since it's built-in
        self.base_classes = []

    def render(self, *, class_name: str | None = None) -> str:
        """Override render to include locations in template context."""
        return self._render(
            class_name=class_name or self.class_name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
            methods=self.methods,
            description=self.description,
            locations=self.locations,
            **self.extra_template_data,
        )
