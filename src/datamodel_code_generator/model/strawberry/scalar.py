from __future__ import annotations

from datamodel_code_generator.model.scalar import DataTypeScalar as BaseDataTypeScalar


class DataTypeScalar(BaseDataTypeScalar):
    """Strawberry scalar type that doesn't generate TypeAlias definitions."""
    
    TEMPLATE_FILE_PATH: str = "strawberry/Scalar.jinja2"
    DEFAULT_IMPORTS: tuple = ()  # Don't import TypeAlias since we're not generating scalars

