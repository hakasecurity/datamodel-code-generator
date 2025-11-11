from __future__ import annotations

from datamodel_code_generator.model.pydantic.custom_root_type import CustomRootType


class RootModel(CustomRootType):
    TEMPLATE_FILE_PATH: str = "strawberry/RootModel.jinja2"
