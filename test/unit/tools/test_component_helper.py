from deepset_mcp.tools.component_helper import (
    extract_component_info,
    extract_component_texts,
    format_io_info,
)


def test_extract_component_info() -> None:
    component_def = {
        "title": "TestComponent",
        "description": "A test component",
        "properties": {
            "type": {
                "const": "test.component.TestComponent",
                "family": "test_family",
                "family_description": "Test family description",
            },
            "init_parameters": {
                "properties": {
                    "param1": {
                        "_annotation": "str",
                        "description": "First parameter",
                        "default": "default1",
                    },
                    "param2": {
                        "_annotation": "int",
                        "description": "Second parameter",
                    },
                }
            },
        },
    }

    result = extract_component_info({}, component_def)

    assert "Component: test.component.TestComponent" in result
    assert "Name: TestComponent" in result
    assert "Family: test_family" in result
    assert "Family Description: Test family description" in result
    assert "A test component" in result
    assert "param1: str (default: default1)" in result
    assert "First parameter" in result
    assert "param2: int" in result
    assert "Second parameter" in result


def test_format_io_info() -> None:
    io_info = {
        "input": {
            "properties": {
                "input1": {
                    "_annotation": "str",
                    "description": "First input",
                    "default": "default1",
                }
            },
            "required": ["input1"],
        },
        "output": {
            "properties": {
                "output1": {
                    "_annotation": "str",
                    "description": "First output",
                }
            },
            "required": ["output1"],
            "definitions": {
                "SubType": {
                    "properties": {
                        "field1": {
                            "type": "string",
                            "description": "A field",
                        }
                    },
                    "required": ["field1"],
                }
            },
        },
    }

    result = format_io_info(io_info)

    assert "Input Schema:" in result
    assert "input1: str (required) (default: default1)" in result
    assert "First input" in result
    assert "Output Schema:" in result
    assert "output1: str (required)" in result
    assert "First output" in result
    assert "Definitions:" in result
    assert "SubType:" in result
    assert "field1: string (required)" in result
    assert "A field" in result


def test_extract_component_texts() -> None:
    component_def = {
        "title": "TestComponent",
        "description": "A test component",
        "properties": {
            "type": {
                "const": "test.component.TestComponent",
            },
        },
    }

    component_type, text = extract_component_texts(component_def)

    assert component_type == "test.component.TestComponent"
    assert text == "TestComponent A test component"
