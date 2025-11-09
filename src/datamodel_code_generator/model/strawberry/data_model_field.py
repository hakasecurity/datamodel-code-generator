"""Strawberry GraphQL DataModelField implementation.

This module inherits from PydanticDataModelField to reuse Pydantic's field parsing
while customizing only the output format, and overrides only the field-specific behaviors needed for Strawberry:

1. Custom field() property: Generates `strawberry.field(name='...')` for aliased fields
   (e.g., Python reserved keywords like 'from' become 'from_')
2. Custom imports: Prevents importing `pydantic.Field` which is not needed
3. Type hint resolution: Maps GraphQL scalar types (String, Int, etc.) to Python native types
4. Enum default formatting: Properly formats enum defaults as EnumName.VALUE

This enables Strawberry to reuse all of Pydantic's field parsing logic while
generating Strawberry-specific field syntax.
"""
from __future__ import annotations

from datamodel_code_generator.model.pydantic.base_model import DataModelField as PydanticDataModelField


class DataModelField(PydanticDataModelField):
    """Strawberry GraphQL field model.

    Generates field definitions with strawberry.field() for aliased fields,
    inheriting all parsing logic from Pydantic.
    """
    @property
    def type_hint(self) -> str:
        """
        Override to resolve GraphQL scalar types to Python native types for Strawberry.

        Strawberry uses native Python types (str, int, bool) instead of TypeAlias references.
        """
        from datamodel_code_generator.model.scalar import DataTypeScalar
        import re

        # Get the original type hint
        original_hint = super().type_hint

        # Check if any of the data types reference a scalar
        # If so, replace the scalar reference with the Python type
        graphql_scalar_map = {
            "String": "str",
            "Int": "int",
            "Float": "float",
            "Boolean": "bool",
            "ID": "ID",  # ID remains as strawberry.ID (handled by imports)
        }

        # Track if we need to add ID import
        self._uses_id = False

        # Replace scalar type aliases with Python types in the type hint
        # Use word boundaries to avoid replacing parts of other words
        for scalar_name, python_type in graphql_scalar_map.items():
            # Check if this scalar is actually referenced in the data type
            for data_type in self.data_type.all_data_types:
                if data_type.reference and isinstance(data_type.reference.source, DataTypeScalar):
                    # Check both the original name and the reference name (which might have "Model" suffix)
                    ref_name = data_type.reference.name
                    orig_name = data_type.reference.original_name

                    if orig_name == scalar_name or ref_name == scalar_name or ref_name == f"{scalar_name}Model":
                        # Use regex with word boundaries to replace the type name
                        # Handle both "ScalarName" and "ScalarNameModel" patterns
                        pattern = r'\b' + re.escape(scalar_name) + r'(Model)?\b'
                        original_hint = re.sub(pattern, python_type, original_hint)
                        # Mark that we're using ID
                        if scalar_name == "ID":
                            self._uses_id = True
                        break  # Only replace once per scalar type

        return original_hint

    @property
    def field(self) -> str | None:
        """Generate strawberry.field(name='...') for reserved keyword fields."""
        # Check if field has an alias (meaning it's a reserved keyword or renamed field)
        if self.alias:
            # Generate strawberry.field(name='original_name') or strawberry.field(name='original_name', default=value)
            if self.has_default and self.represented_default and self.represented_default != 'None':
                # Use represented_default which is already properly formatted
                return f"strawberry.field(name='{self.alias}', default={self.represented_default})"
            else:
                return f"strawberry.field(name='{self.alias}')"

        # For non-aliased fields, don't return any field decorator (None means no decorator)
        return None

    @property
    def represented_default(self) -> str:
        """
        Override to properly format enum defaults for Strawberry.

        When the default is a string and the field type references an enum,
        format it as 'EnumName.VALUE' so the Jinja template can properly unquote it.
        """
        from datamodel_code_generator.model.enum import Enum

        # If default is already a Member object, use parent's repr
        if hasattr(self.default, 'enum') and hasattr(self.default, 'field'):
            return super().represented_default

        # Check if this field has an enum type
        if self.default and isinstance(self.default, str):
            # Check all data types in the type hierarchy
            for data_type in self.data_type.all_data_types:
                if data_type.reference and isinstance(data_type.reference.source, Enum):
                    # Format as 'EnumName.VALUE' so template can unquote it
                    enum_name = data_type.reference.name
                    if isinstance(self.default, list):
                        # Handle list of enum values
                        return repr([f"{enum_name}.{val}" for val in self.default])
                    return repr(f"{enum_name}.{self.default}")

        return super().represented_default

    @property
    def imports(self) -> tuple:
        """Override to not import pydantic Field for strawberry fields, and add ID import if needed."""
        from datamodel_code_generator.model.base import DataModelFieldBase
        from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_ID

        # Get base imports
        base_imports = DataModelFieldBase.imports.fget(self)

        # Add ID import if this field uses the ID type
        if hasattr(self, '_uses_id') and self._uses_id:
            return (*base_imports, IMPORT_STRAWBERRY_ID)

        return base_imports
