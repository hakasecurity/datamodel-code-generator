from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from datamodel_code_generator import DataModelType, generate, InputFileType

EXPECTED_DIR = Path(__file__).parent.parent / "data" / "expected" / "parser" / "graphql" / "strawberry"


write_expected = False

def write_expected_file(expected_file: str, content: str):
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXPECTED_DIR / expected_file, 'w') as f:
        f.write(content)


def generate_strawberry_code(graphql_schema: str, **kwargs):
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.Strawberry,
            output=output_path,
            disable_timestamp=True,
            use_union_operator=True,
            **kwargs,
        )

        return output_path.read_text()
    finally:
        output_path.unlink()


def test_graphql_builtin_types():
    """Test that GraphQL built-in types are mapped correctly."""
    graphql_schema = """
    type Test {
        stringField: String!
        intField: Int!
        floatField: Float!
        booleanField: Boolean!
        idField: ID!
    }
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("builtin_types.py", result)
    expected = (EXPECTED_DIR / "builtin_types.py").read_text()
    assert result == expected


def test_graphql_enum_generation():
    """Test that GraphQL enums are generated with @strawberry.enum directive."""
    graphql_schema = """
    enum Direction {
        ASC
        DESC
    }
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("enum_generation.py", result)
    expected = (EXPECTED_DIR / "enum_generation.py").read_text()
    assert result == expected


def test_graphql_custom_scalars():
    graphql_schema = """
    scalar Email
    scalar MD5

    type Test {
        email: Email!
        md5: MD5!
    }
    """
    
    result = generate_strawberry_code(graphql_schema, additional_imports=[".custom_types.scalars.*", ".custom_types.enums.*"])
    if write_expected:
        write_expected_file("custom_scalars.py", result)
    expected = (EXPECTED_DIR / "custom_scalars.py").read_text()
    assert result == expected


def test_graphql_nullable_and_non_nullable_fields():
    """Test that nullable and non-nullable GraphQL fields are generated correctly."""
    graphql_schema = """
    type User {
        id: ID!
        name: String!
        email: String
        age: Int
    }
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("nullable_and_non_nullable_fields.py", result)
    expected = (EXPECTED_DIR / "nullable_and_non_nullable_fields.py").read_text()
    assert result == expected


def test_graphql_input_with_default_values():
    """Test that GraphQL inputs with default values are generated correctly."""
    graphql_schema = """
    input PagingInput {
        limit: Int! = 100
        from: Int = 0
    }

    enum Direction {
        ASC
        DESC
    }
    
    input Sort {
        direction: Direction! = ASC
    }

    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("input_with_default_values.py", result)
    expected = (EXPECTED_DIR / "input_with_default_values.py").read_text()
    assert result == expected


def test_graphql_list_types():
    """Test that GraphQL list types are generated correctly."""
    graphql_schema = """
    type User {
        id: ID!
        tags: [String!]!
        optionalTags: [String!]
    }
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("list_types.py", result)
    expected = (EXPECTED_DIR / "list_types.py").read_text()
    assert result == expected


def test_graphql_directive_generation():
    """Test that GraphQL directives without parameters include pass."""
    graphql_schema = """
    directive @beta on FIELD_DEFINITION
    directive @foo(name: String, bar: Boolean) on INPUT_FIELD_DEFINITION | FIELD_DEFINITION

    enum Status {
        ACTIVE
        INACTIVE
    }

    directive @config(
        ## Known issue:
        ## 1. non-nullable arguments are generated with Optional wrapper
        ## 2. arguments without default are not initialized to None
        name: String
        required: Boolean!
        required_with_default: Boolean! = true
        maxInt: Int! = 100
        minInt: Int! = 0
        maxFloat: Float! = 3.14
        enabled: Boolean! = true
        disabled: Boolean! = false
        message: String! = "Hello"
        status: Status! = ACTIVE
        optionalInt: Int = 42
        optionalString: String = "default"
    ) on FIELD_DEFINITION
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("directive.py", result)
    expected = (EXPECTED_DIR / "directive.py").read_text()
    assert result == expected

def test_graphql_builtin_directives_not_generated():
    """Test that built-in GraphQL directives are not generated."""
    graphql_schema = """
    directive @deprecated(
        reason: String = "No longer supported"
    ) on FIELD_DEFINITION | ENUM_VALUE

    directive @beta on FIELD_DEFINITION
    
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("builtin_directives_not_generated.py", result)
    expected = (EXPECTED_DIR / "builtin_directives_not_generated.py").read_text()
    assert result == expected
        

def test_graphql_complex_schema():
    """Test a complex GraphQL schema with multiple types."""
    graphql_schema = """
    enum UserStatus {
        ACTIVE
        INACTIVE
        PENDING
    }
    
    input CreateUserInput {
        name: String!
        email: String!
        status: UserStatus = ACTIVE
    }
    
    type User {
        id: ID!
        name: String!
        email: String!
        status: UserStatus!
    }
    
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("complex_schema.py", result)
    expected = (EXPECTED_DIR / "complex_schema.py").read_text()
    assert result == expected


def test_graphql_reserved_keyword_fields():
    """Test that fields with Python reserved keyword names get @strawberry.field decorator."""
    graphql_schema = """
    type Test {
        in: String!
        from: Int!
        name: String!
    }
    
    input TestInput {
        in: String!
        from: Int!
        name: String!
    }
    """
    
    result = generate_strawberry_code(graphql_schema)
    if write_expected:
        write_expected_file("reserved_keyword_fields.py", result)
    expected = (EXPECTED_DIR / "reserved_keyword_fields.py").read_text()
    assert result == expected
