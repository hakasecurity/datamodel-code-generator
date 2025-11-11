"""Strawberry GraphQL BaseModel implementation.

This module inherits from PydanticBaseModel to reuse Pydantic's parsing and model generation
while customizing only the output format:
1. Inherits from PydanticBaseModel to reuse all parsing logic
2. Overrides DEFAULT_IMPORTS to prevent importing pydantic-specific imports
3. Uses Strawberry-specific templates (strawberry/BaseModel.jinja2)
4. Adds Strawberry-specific imports (strawberry.type, strawberry.scalars)

This approach eliminates the need for a separate StrawberryGraphQLParser (~800 lines)
while maintaining full Strawberry GraphQL functionality through template customization.
"""
from __future__ import annotations

from datamodel_code_generator.model.pydantic.base_model import BaseModel as PydanticBaseModel
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_TYPE, IMPORT_STRAWBERRY_SCALARS


class BaseModel(PydanticBaseModel):
    """Strawberry GraphQL type model.

    Generates @strawberry.type decorated classes by inheriting Pydantic's
    model generation and customizing the output template and imports.
    """
    TEMPLATE_FILE_PATH: str = "strawberry/BaseModel.jinja2"
    BASE_CLASS: str = "object"
    DECORATOR: str = "@strawberry.type"
    # Override DEFAULT_IMPORTS to prevent pydantic.BaseModel import
    # Strawberry doesn't need Pydantic imports - it uses decorators instead
    DEFAULT_IMPORTS: tuple = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Strawberry-specific imports
        self._additional_imports.append(IMPORT_STRAWBERRY_TYPE)
        self._additional_imports.append(IMPORT_STRAWBERRY_SCALARS)

    def set_base_class(self) -> None:
        """Override to not import built-in Python types.

        Strawberry types don't inherit from any base class,
        they use decorators instead. This prevents importing 'object'.
        """
        self.base_classes = []

    @property
    def imports(self) -> tuple[Import, ...]:
        """Override to filter out Literal import if only used for __typename field."""
        from datamodel_code_generator.imports import IMPORT_LITERAL

        base_imports = super().imports

        # Check if Literal is only used for __typename field (which we filter out in template)
        # If so, remove it from imports
        has_literal = any(imp == IMPORT_LITERAL for imp in base_imports)
        if has_literal:
            # Check if any non-__typename field uses Literal
            uses_literal_elsewhere = any(
                field.name != 'typename__' and 'Literal' in field.type_hint
                for field in self.fields
            )
            if not uses_literal_elsewhere:
                # Filter out Literal import
                return tuple(imp for imp in base_imports if imp != IMPORT_LITERAL)

        return base_imports
