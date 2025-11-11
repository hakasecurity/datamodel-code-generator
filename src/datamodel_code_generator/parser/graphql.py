from __future__ import annotations

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
)
from urllib.parse import ParseResult

from datamodel_code_generator import (
    DefaultPutDict,
    LiteralType,
    PythonVersion,
    PythonVersionMin,
    snooper_to_methods,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.model.scalar import DataTypeScalar
from datamodel_code_generator.model.union import DataTypeUnion
from datamodel_code_generator.parser.base import (
    DataType,
    Parser,
    Source,
    escape_characters,
)
from datamodel_code_generator.reference import ModelType, Reference
from datamodel_code_generator.types import DataTypeManager, StrictTypes, Types

try:
    import graphql
except ImportError as exc:  # pragma: no cover
    msg = "Please run `$pip install 'datamodel-code-generator[graphql]`' to generate data-model from a GraphQL schema."
    raise Exception(msg) from exc  # noqa: TRY002


from datamodel_code_generator.format import DEFAULT_FORMATTERS, DatetimeClassType, Formatter

if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Iterable, Iterator, Mapping, Sequence

graphql_resolver = graphql.type.introspection.TypeResolvers()


def build_graphql_schema(schema_str: str) -> graphql.GraphQLSchema:
    """Build a graphql schema from a string."""
    schema = graphql.build_schema(schema_str)
    return graphql.lexicographic_sort_schema(schema)


@snooper_to_methods()
class GraphQLParser(Parser):
    # raw graphql schema as `graphql-core` object
    raw_obj: graphql.GraphQLSchema
    # all processed graphql objects
    # mapper from an object name (unique) to an object
    all_graphql_objects: dict[str, graphql.GraphQLNamedType]
    # a reference for each object
    # mapper from an object name to his reference
    references: dict[str, Reference] = {}  # noqa: RUF012
    # mapper from graphql type to all objects with this type
    # `graphql.type.introspection.TypeKind` -- an enum with all supported types
    # `graphql.GraphQLNamedType` -- base type for each graphql object
    # see `graphql-core` for more details
    support_graphql_types: dict[graphql.type.introspection.TypeKind, list[graphql.GraphQLNamedType]]
    # graphql types order for render
    # may be as a parameter in the future
    parse_order: list[graphql.type.introspection.TypeKind] = [  # noqa: RUF012
        graphql.type.introspection.TypeKind.SCALAR,
        graphql.type.introspection.TypeKind.ENUM,
        graphql.type.introspection.TypeKind.INTERFACE,
        graphql.type.introspection.TypeKind.OBJECT,
        graphql.type.introspection.TypeKind.INPUT_OBJECT,
        graphql.type.introspection.TypeKind.UNION,
    ]

    def __init__(  # noqa: PLR0913
        self,
        source: str | Path | ParseResult,
        *,
        data_model_type: type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: type[DataModel] = pydantic_model.CustomRootType,
        data_model_scalar_type: type[DataModel] = DataTypeScalar,
        data_model_union_type: type[DataModel] = DataTypeUnion,
        # Add support for different model types per GraphQL construct
        # to allow frameworks like Strawberry to use the generic GraphQL parser
        # while providing their own model implementations without requiring a separate parser
        data_model_input_type: type[DataModel] | None = None,  # For GraphQL input types
        data_model_enum_type: type[DataModel] | None = None,  # For GraphQL enum types
        data_model_directive_type: type[DataModel] | None = None,  # For GraphQL directives
        data_type_manager_type: type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: str | None = None,
        additional_imports: list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        target_python_version: PythonVersion = PythonVersionMin,
        dump_resolve_reference_action: Callable[[Iterable[str]], str] | None = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Mapping[str, str] | None = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        allow_extra_fields: bool = False,
        extra_fields: str | None = None,
        force_optional_for_required_fields: bool = False,
        class_name: str | None = None,
        use_standard_collections: bool = False,
        base_path: Path | None = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        encoding: str = "utf-8",
        enum_field_as_literal: LiteralType | None = None,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: DefaultPutDict[str, str] | None = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Sequence[StrictTypes] | None = None,
        empty_enum_field_name: str | None = None,
        custom_class_name_generator: Callable[[str], str] | None = None,
        field_extra_keys: set[str] | None = None,
        field_include_all_keys: bool = False,
        field_extra_keys_without_x_prefix: set[str] | None = None,
        wrap_string_literal: bool | None = None,
        use_title_as_name: bool = False,
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
        http_headers: Sequence[tuple[str, str]] | None = None,
        http_ignore_tls: bool = False,
        use_annotated: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        original_field_name_delimiter: str | None = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
        use_one_literal_as_default: bool = False,
        known_third_party: list[str] | None = None,
        custom_formatters: list[str] | None = None,
        custom_formatters_kwargs: dict[str, Any] | None = None,
        use_pendulum: bool = False,
        http_query_parameters: Sequence[tuple[str, str]] | None = None,
        treat_dot_as_module: bool = False,
        use_exact_imports: bool = False,
        default_field_extras: dict[str, Any] | None = None,
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
        keyword_only: bool = False,
        frozen_dataclasses: bool = False,
        no_alias: bool = False,
        formatters: list[Formatter] = DEFAULT_FORMATTERS,
        parent_scoped_naming: bool = False,
    ) -> None:
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_type_manager_type=data_type_manager_type,
            data_model_field_type=data_model_field_type,
            base_class=base_class,
            additional_imports=additional_imports,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            target_python_version=target_python_version,
            dump_resolve_reference_action=dump_resolve_reference_action,
            validation=validation,
            field_constraints=field_constraints,
            snake_case_field=snake_case_field,
            strip_default_none=strip_default_none,
            aliases=aliases,
            allow_population_by_field_name=allow_population_by_field_name,
            allow_extra_fields=allow_extra_fields,
            extra_fields=extra_fields,
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            force_optional_for_required_fields=force_optional_for_required_fields,
            class_name=class_name,
            use_standard_collections=use_standard_collections,
            base_path=base_path,
            use_schema_description=use_schema_description,
            use_field_description=use_field_description,
            use_default_kwarg=use_default_kwarg,
            reuse_model=reuse_model,
            encoding=encoding,
            enum_field_as_literal=enum_field_as_literal,
            use_one_literal_as_default=use_one_literal_as_default,
            set_default_enum_member=set_default_enum_member,
            use_subclass_enum=use_subclass_enum,
            strict_nullable=strict_nullable,
            use_generic_container_types=use_generic_container_types,
            enable_faux_immutability=enable_faux_immutability,
            remote_text_cache=remote_text_cache,
            disable_appending_item_suffix=disable_appending_item_suffix,
            strict_types=strict_types,
            empty_enum_field_name=empty_enum_field_name,
            custom_class_name_generator=custom_class_name_generator,
            field_extra_keys=field_extra_keys,
            field_include_all_keys=field_include_all_keys,
            field_extra_keys_without_x_prefix=field_extra_keys_without_x_prefix,
            wrap_string_literal=wrap_string_literal,
            use_title_as_name=use_title_as_name,
            use_operation_id_as_name=use_operation_id_as_name,
            use_unique_items_as_set=use_unique_items_as_set,
            http_headers=http_headers,
            http_ignore_tls=http_ignore_tls,
            use_annotated=use_annotated,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            original_field_name_delimiter=original_field_name_delimiter,
            use_double_quotes=use_double_quotes,
            use_union_operator=use_union_operator,
            allow_responses_without_content=allow_responses_without_content,
            collapse_root_models=collapse_root_models,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
            keep_model_order=keep_model_order,
            known_third_party=known_third_party,
            custom_formatters=custom_formatters,
            custom_formatters_kwargs=custom_formatters_kwargs,
            use_pendulum=use_pendulum,
            http_query_parameters=http_query_parameters,
            treat_dot_as_module=treat_dot_as_module,
            use_exact_imports=use_exact_imports,
            default_field_extras=default_field_extras,
            target_datetime_class=target_datetime_class,
            keyword_only=keyword_only,
            frozen_dataclasses=frozen_dataclasses,
            no_alias=no_alias,
            formatters=formatters,
            parent_scoped_naming=parent_scoped_naming,
        )

        self.data_model_scalar_type = data_model_scalar_type
        self.data_model_union_type = data_model_union_type
        # Store model types with fallbacks to support both Pydantic and Strawberry
        # If specific types aren't provided, fall back to the generic data_model_type
        # This enables reusing the same parser for different frameworks
        self.data_model_input_type = data_model_input_type or data_model_type
        self.data_model_enum_type = data_model_enum_type or Enum
        self.data_model_directive_type = data_model_directive_type  # No fallback - directives are optional
        self.use_standard_collections = use_standard_collections
        self.use_union_operator = use_union_operator

    def _get_context_source_path_parts(self) -> Iterator[tuple[Source, list[str]]]:
        # TODO (denisart): Temporarily this method duplicates
        # the method `datamodel_code_generator.parser.jsonschema.JsonSchemaParser._get_context_source_path_parts`.

        if isinstance(self.source, list) or (  # pragma: no cover
            isinstance(self.source, Path) and self.source.is_dir()
        ):  # pragma: no cover
            self.current_source_path = Path()
            self.model_resolver.after_load_files = {
                self.base_path.joinpath(s.path).resolve().as_posix() for s in self.iter_source
            }

        for source in self.iter_source:
            if isinstance(self.source, ParseResult):  # pragma: no cover
                path_parts = self.get_url_path_parts(self.source)
            else:
                path_parts = list(source.path.parts)
            if self.current_source_path is not None:  # pragma: no cover
                self.current_source_path = source.path
            with (
                self.model_resolver.current_base_path_context(source.path.parent),
                self.model_resolver.current_root_context(path_parts),
            ):
                yield source, path_parts

    def _resolve_types(self, paths: list[str], schema: graphql.GraphQLSchema) -> None:
        """Resolve and register GraphQL types for code generation.

        Enhanced to handle built-in scalars as referenceable types.
        Previously, built-in scalars were skipped entirely. Now they're registered
        so that frameworks like Strawberry can map them to their own types
        (e.g., GraphQL ID -> strawberry.ID) via templates.
        """
        # Built-in GraphQL scalar types
        builtin_scalars = {"String", "Int", "Float", "Boolean", "ID"}

        for type_name, type_ in schema.type_map.items():
            if type_name.startswith("__"):
                continue

            if type_name in {"Query", "Mutation"}:
                continue

            resolved_type = graphql_resolver.kind(type_, None)

            # For built-in scalars, add them to references so fields can reference them
            # The actual rendering (as TypeAlias or native types) is handled by templates
            if type_name in builtin_scalars:
                if resolved_type == graphql.type.introspection.TypeKind.SCALAR:
                    self.all_graphql_objects[type_.name] = type_
                    self.references[type_.name] = Reference(
                        path=f"{paths!s}/{resolved_type.value}/{type_.name}",
                        name=type_.name,
                        original_name=type_.name,
                    )
                    self.support_graphql_types[resolved_type].append(type_)
                continue

            # Skip custom scalar types (they should be provided via additional_imports)
            if resolved_type == graphql.type.introspection.TypeKind.SCALAR:
                continue

            if resolved_type in self.support_graphql_types:  # pragma: no cover
                self.all_graphql_objects[type_.name] = type_
                # TODO: need a special method for each graph type
                self.references[type_.name] = Reference(
                    path=f"{paths!s}/{resolved_type.value}/{type_.name}",
                    name=type_.name,
                    original_name=type_.name,
                )

                self.support_graphql_types[resolved_type].append(type_)

    def _create_data_model(self, model_type: type[DataModel] | None = None, **kwargs: Any) -> DataModel:
        """Create data model instance with conditional frozen parameter for DataClass."""
        data_model_class = model_type or self.data_model_type
        if issubclass(data_model_class, DataClass):
            kwargs["frozen"] = self.frozen_dataclasses
        return data_model_class(**kwargs)

    def _typename_field(self, name: str) -> DataModelFieldBase:
        return self.data_model_field_type(
            name="typename__",
            data_type=DataType(
                literals=[name],
                use_union_operator=self.use_union_operator,
                use_standard_collections=self.use_standard_collections,
            ),
            default=name,
            use_annotated=self.use_annotated,
            required=False,
            alias="__typename",
            use_one_literal_as_default=True,
            use_default_kwarg=self.use_default_kwarg,
            has_default=True,
        )

    def _get_default(
        self,
        field: graphql.GraphQLField | graphql.GraphQLInputField | graphql.GraphQLArgument,
        final_data_type: DataType,
        required: bool,  # noqa: FBT001
    ) -> Any:
        """Get the default value for a GraphQL field.

        Extended to handle GraphQLArgument in addition to GraphQLInputField.
        This is necessary for parsing directive arguments, which were not supported
        in the original implementation. Directive support eliminates the need for
        a separate parser for directives.
        """
        # Handle default values for input fields and directive arguments
        if isinstance(field, (graphql.GraphQLInputField, graphql.GraphQLArgument)):  # pragma: no cover
            if field.default_value == graphql.pyutils.Undefined:  # pragma: no cover
                return None
            # Check if the field type is an enum
            field_type = field.type
            # Check for list wrapping
            is_list_type = False
            while graphql.is_wrapping_type(field_type):
                if graphql.is_list_type(field_type):
                    is_list_type = True
                field_type = field_type.of_type
            if graphql.is_enum_type(field_type):
                # For enum defaults, just return the value name(s)
                # The __set_default_enum_member method will convert to proper enum members
                return field.default_value
            return field.default_value
        if required is False and final_data_type.is_list:
            return None

        return None

    def parse_scalar(self, scalar_graphql_object: graphql.GraphQLScalarType) -> None:
        self.results.append(
            self.data_model_scalar_type(
                reference=self.references[scalar_graphql_object.name],
                fields=[],
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                description=scalar_graphql_object.description,
            )
        )

    def parse_enum(self, enum_object: graphql.GraphQLEnumType) -> None:
        enum_fields: list[DataModelFieldBase] = []
        exclude_field_names: set[str] = set()

        for value_name, value in enum_object.values.items():
            default = f"'{value_name.translate(escape_characters)}'" if isinstance(value_name, str) else value_name

            field_name = self.model_resolver.get_valid_field_name(
                value_name, excludes=exclude_field_names, model_type=ModelType.ENUM
            )
            exclude_field_names.add(field_name)

            enum_fields.append(
                self.data_model_field_type(
                    name=field_name,
                    data_type=self.data_type_manager.get_data_type(
                        Types.string,
                    ),
                    default=default,
                    required=True,
                    strip_default_none=self.strip_default_none,
                    has_default=True,
                    use_field_description=value.description is not None,
                    original_name=None,
                )
            )

        enum = self.data_model_enum_type(
            reference=self.references[enum_object.name],
            fields=enum_fields,
            path=self.current_source_path,
            description=enum_object.description,
            custom_template_dir=self.custom_template_dir,
        )
        self.results.append(enum)

    def parse_field(
        self,
        field_name: str,
        alias: str | None,
        field: graphql.GraphQLField | graphql.GraphQLInputField | graphql.GraphQLArgument,
    ) -> DataModelFieldBase:
        """Parse a GraphQL field into a data model field.

        Extended to handle GraphQLArgument for directive arguments.
        Also enhanced to properly handle default values and nullable constraints
        for non-null types with defaults (e.g., Boolean! = true should generate
        `bool = True` not `bool | None = True`).
        """
        final_data_type = DataType(
            is_optional=True,
            use_union_operator=self.use_union_operator,
            use_standard_collections=self.use_standard_collections,
        )
        data_type = final_data_type
        obj = field.type

        while graphql.is_list_type(obj) or graphql.is_non_null_type(obj):
            if graphql.is_list_type(obj):
                data_type.is_list = True

                new_data_type = DataType(
                    is_optional=True,
                    use_union_operator=self.use_union_operator,
                    use_standard_collections=self.use_standard_collections,
                )
                data_type.data_types = [new_data_type]

                data_type = new_data_type
            elif graphql.is_non_null_type(obj):  # pragma: no cover
                data_type.is_optional = False

            obj = graphql.assert_wrapping_type(obj)
            obj = obj.of_type

        if graphql.is_enum_type(obj):
            obj = graphql.assert_enum_type(obj)
            data_type.reference = self.references[obj.name]

        obj = graphql.assert_named_type(obj)

        # Check if this is a type we have a reference for (including built-in scalars)
        if obj.name in self.references:
            data_type.reference = self.references[obj.name]
        else:
            # For types without references (custom scalars), use the type name directly
            data_type.type = obj.name

        # Check if field has a default value (for arguments and input fields)
        has_default_value = (
            isinstance(field, (graphql.GraphQLInputField, graphql.GraphQLArgument))
            and field.default_value != graphql.pyutils.Undefined
        )

        # A field is required only if it's not optional and doesn't have a default value
        required = (
            (not self.force_optional_for_required_fields)
            and (not final_data_type.is_optional)
            and (not has_default_value)
        )

        default = self._get_default(field, final_data_type, required)
        extras = {} if self.default_field_extras is None else self.default_field_extras.copy()

        if field.description is not None:  # pragma: no cover
            extras["description"] = field.description

        # For fields with non-null types that have defaults, we need to set nullable=False
        # explicitly to prevent the type from becoming optional (e.g. bool | None)
        # even though required=False
        nullable = None
        if has_default_value and not final_data_type.is_optional:
            nullable = False

        return self.data_model_field_type(
            name=field_name,
            default=default,
            data_type=final_data_type,
            required=required,
            extras=extras,
            alias=alias,
            strip_default_none=self.strip_default_none,
            use_annotated=self.use_annotated,
            use_field_description=self.use_field_description,
            use_default_kwarg=self.use_default_kwarg,
            original_name=field_name,
            has_default=default is not None,
            nullable=nullable,
        )

    def parse_object_like(
        self,
        obj: graphql.GraphQLInterfaceType | graphql.GraphQLObjectType | graphql.GraphQLInputObjectType,
    ) -> None:
        fields = []
        exclude_field_names: set[str] = set()

        for field_name, field in obj.fields.items():
            field_name_, alias = self.model_resolver.get_valid_field_name_and_alias(
                field_name, excludes=exclude_field_names
            )
            exclude_field_names.add(field_name_)

            data_model_field_type = self.parse_field(field_name_, alias, field)
            fields.append(data_model_field_type)

        # Always add __typename field for GraphQL types (templates can filter it out)
        fields.append(self._typename_field(obj.name))

        base_classes = []
        if hasattr(obj, "interfaces"):  # pragma: no cover
            base_classes = [self.references[i.name] for i in obj.interfaces]  # pyright: ignore[reportAttributeAccessIssue]

        data_model_type = self._create_data_model(
            reference=self.references[obj.name],
            fields=fields,
            base_classes=base_classes,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description,
            keyword_only=self.keyword_only,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.results.append(data_model_type)

    def parse_interface(self, interface_graphql_object: graphql.GraphQLInterfaceType) -> None:
        self.parse_object_like(interface_graphql_object)

    def parse_object(self, graphql_object: graphql.GraphQLObjectType) -> None:
        self.parse_object_like(graphql_object)

    def parse_input_object(self, input_graphql_object: graphql.GraphQLInputObjectType) -> None:
        """Parse a GraphQL input object type into a data model.

        Overridden to explicitly use `self.data_model_input_type` instead
        of reusing `parse_object_like`. This allows Strawberry to provide its own
        Input implementation with the @strawberry.input decorator. Previously, this
        just called parse_object_like which didn't distinguish between types and inputs.
        """
        # Parse fields using the same logic as parse_object
        fields: list[DataModelFieldBase] = []
        exclude_field_names: set[str] = set()

        for field_name, field in input_graphql_object.fields.items():
            alias_name = self.model_resolver.get_valid_field_name(
                field_name, excludes=exclude_field_names
            )
            exclude_field_names.add(alias_name)

            fields.append(
                self.parse_field(
                    field_name=alias_name,
                    alias=field_name if alias_name != field_name else None,
                    field=field,
                )
            )

        # Always add __typename field for GraphQL types (templates can filter it out)
        fields.append(self._typename_field(input_graphql_object.name))

        # Use Input model type instead of regular BaseModel
        data_model = self.data_model_input_type(
            reference=self.references[input_graphql_object.name],
            fields=fields,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=input_graphql_object.description,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.results.append(data_model)

    def parse_union(self, union_object: graphql.GraphQLUnionType) -> None:
        fields = [self.data_model_field_type(name=type_.name, data_type=DataType()) for type_ in union_object.types]

        data_model_type = self.data_model_union_type(
            reference=self.references[union_object.name],
            fields=fields,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=union_object.description,
        )
        self.results.append(data_model_type)

    def parse_raw(self) -> None:
        self.all_graphql_objects = {}
        self.references: dict[str, Reference] = {}

        self.support_graphql_types = {
            graphql.type.introspection.TypeKind.SCALAR: [],
            graphql.type.introspection.TypeKind.ENUM: [],
            graphql.type.introspection.TypeKind.UNION: [],
            graphql.type.introspection.TypeKind.INTERFACE: [],
            graphql.type.introspection.TypeKind.OBJECT: [],
            graphql.type.introspection.TypeKind.INPUT_OBJECT: [],
        }

        # may be as a parameter in the future (??)
        mapper_from_graphql_type_to_parser_method = {
            graphql.type.introspection.TypeKind.SCALAR: self.parse_scalar,
            graphql.type.introspection.TypeKind.ENUM: self.parse_enum,
            graphql.type.introspection.TypeKind.INTERFACE: self.parse_interface,
            graphql.type.introspection.TypeKind.OBJECT: self.parse_object,
            graphql.type.introspection.TypeKind.INPUT_OBJECT: self.parse_input_object,
            graphql.type.introspection.TypeKind.UNION: self.parse_union,
        }

        for source, path_parts in self._get_context_source_path_parts():
            schema: graphql.GraphQLSchema = build_graphql_schema(source.text)
            self.raw_obj = schema

            self._resolve_types(path_parts, schema)

            for next_type in self.parse_order:
                for obj in self.support_graphql_types[next_type]:
                    parser_ = mapper_from_graphql_type_to_parser_method[next_type]
                    parser_(obj)

            # Parse directives if we have a directive model type
            if self.data_model_directive_type:
                self._parse_directives(schema)

    def _parse_directives(self, schema: graphql.GraphQLSchema) -> None:
        """Parse GraphQL directives and generate directive classes.

        Added directive parsing support to the generic GraphQL parser.
        This method is now called conditionally when `data_model_directive_type` is
        provided, eliminating the need for a separate parser implementation.

        Key features:
        - Filters out built-in GraphQL directives (skip, include, deprecated, specifiedBy)
        - Parses directive arguments as fields
        - Converts directive locations to framework-specific location enums
        - Uses unique paths to prevent directives from overwriting each other
        """
        # Built-in GraphQL directives that should not be generated
        builtin_directives = {'skip', 'include', 'deprecated', 'specifiedBy'}

        for directive in schema.directives:
            directive_name = directive.name
            if directive_name in builtin_directives:
                continue

            # Parse directive arguments as fields
            fields: list[DataModelFieldBase] = []
            exclude_field_names: set[str] = set()

            for arg_name, arg in directive.args.items():
                alias_name = self.model_resolver.get_valid_field_name(
                    arg_name, excludes=exclude_field_names
                )
                exclude_field_names.add(alias_name)

                fields.append(
                    self.parse_field(
                        field_name=alias_name,
                        alias=arg_name if alias_name != arg_name else None,
                        field=arg,
                    )
                )

            # Convert directive locations to strawberry Location enums
            locations = [loc.name for loc in directive.locations]

            # Create reference for the directive
            # Use directive name as part of path to ensure uniqueness
            class_name = self.model_resolver.get_class_name(directive_name)

            # Create a unique path for each directive by appending the directive name
            # This prevents directives from overwriting each other in sort_data_models
            base_path = str(self.current_source_path) if self.current_source_path else ""
            directive_path = f"{base_path}#{directive_name}" if base_path else directive_name

            reference = Reference(
                name=class_name.name,  # Extract string name from ClassName object
                path=directive_path,
                original_name=directive_name,
            )
            self.references[directive_name] = reference

            # Create directive model
            directive_model = self.data_model_directive_type(
                reference=reference,
                fields=fields,
                custom_base_class=self.base_class,
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                path=self.current_source_path,
                description=directive.description,
                treat_dot_as_module=self.treat_dot_as_module,
                locations=locations,
            )
            self.results.append(directive_model)
