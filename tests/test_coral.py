from typing import Generator, Optional
import pytest
from jinja2 import Environment, FileSystemLoader
import xml.etree.ElementTree as ET
from contextlib import contextmanager
import logging
from src.coral import (
    JsonNodeBuilder,
    Node,
    NodeAttributesRenderereVisitor,
    NodeGenerator,
    Settings,
    TemplateEngine,
    XmlNodeBuilder,
    apply_functions,
    iter_tree,
    map_func,
    prepare_paths,
    remove_dups,
)
from pathlib import Path


@contextmanager
def temporary_files(
    file_dict: dict[str, str], prefix: Optional[str] = None
) -> Generator[None, None, None]:
    """
    A context manager to create temporary files from a dictionary and ensure they are deleted afterward.

    This context manager writes files specified in `file_dict` to disk, optionally within a given `prefix` directory.
    After the context exits, all created files are deleted.

    :param file_dict: A dictionary where keys are file paths (relative to the prefix, if provided) and values are the content to write to each file.
    :param prefix: Optional directory prefix to prepend to each file path. Defaults to None.
    :yield: Yields control back to the calling context.
    """
    paths = []  # List to store the paths of created files
    try:
        # Iterate over the items in the file_dict
        for filepath, content in file_dict.items():
            # Determine the full path to the file, optionally adding the prefix
            if prefix:
                path = Path(".") / prefix / filepath
            else:
                path = Path(".") / filepath

            # Create the parent directory if it doesn't exist
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file content to the specified path
            logging.debug(f"Wrote {path.resolve()}")
            path.write_text(content)

            # Store the path for later cleanup
            paths.append(path)

        # Yield control back to the calling context
        yield
    finally:
        # Clean up: remove all the created files
        for path in paths:
            if path.exists():
                path.unlink()


@pytest.fixture
def settings() -> Settings:
    return Settings()


def test__apply_functions():
    assert apply_functions([], 3) == 3
    assert apply_functions([str], 3) == "3"


def test__remove_dups():
    assert remove_dups([1, 2, 3, 1, 2, 3]) == [1, 2, 3]


def test__iter_tree():
    assert list(iter_tree(Path("/a/b/c"))) == [
        Path("/a/b/c"),
        Path("/a/b"),
        Path("/a"),
        Path("/"),
    ], list(iter_tree(Path("/a/b/c").resolve()))


def test__map_func():
    assert list(map_func(lambda n: n * 2)([1, 2, 3])) == [2, 4, 6]


def test__prepare_paths(settings: Settings) -> None:
    value = prepare_paths(settings, ["/a/b/c", "/d/e"])
    assert value == [
        Path("/a/b/c") / settings.folder_name,
        Path("/a/b") / settings.folder_name,
        Path("/a") / settings.folder_name,
        Path("/") / settings.folder_name,
        Path("/d/e") / settings.folder_name,
        Path("/d") / settings.folder_name,
    ]


def test__render_simple(settings):
    original = ["/Users/mg", "."]

    paths_base = list(prepare_paths(Settings(), original))

    loader = FileSystemLoader(paths_base)
    env = Environment(loader=loader)

    tpl = "{{ name }}"
    for path in (f"{settings.folder_name}/tpl.j2", f"../{settings.folder_name}/tpl.j2"):
        with temporary_files({path: tpl}):
            template = env.get_template("tpl.j2")
            rendered_content = template.render({"name": "mauro"})
            assert rendered_content == "mauro"


def test__a():
    child1 = Node(name="child1", value=2)
    child2 = Node()
    root_node = Node(name="root", value=1, children=[child1, child2])

    assert root_node.name == "root", root_node.name
    assert root_node.children[0].name == "child1", child1.name
    assert root_node.children[1].name == "root", child2.name


def test__b():
    #
    # Test nodes return proper attributes (when loaded from json)
    #
    json_data = {
        "name": "root",
        "value": 1,
        "children": [{"name": "child1", "value": 2}, {}],
    }

    json_builder = JsonNodeBuilder()
    root_node = json_builder.build(json_data)
    assert root_node.name == "root", root_node.name
    assert root_node.children[0].name == "child1", root_node.children[0]
    assert root_node.children[1].name == "root", root_node.children[1]


def test__c():
    #
    # Test nodes return proper attributes (when loaded from xml)
    #
    xml_data = """
    <root name="root" value="1">
        <child1 name="child1" value="2"></child1>
        <child2></child2>
    </root>
    """

    xml_root = ET.fromstring(xml_data)
    xml_builder = XmlNodeBuilder()
    root_node = xml_builder.build(xml_root)
    assert root_node.name == "root", root_node.name
    assert root_node.children[0].name == "child1", root_node.children[0].name
    assert root_node.children[1].name == "root", root_node.children[1].name


def test__d():
    #
    # Test the template engine
    #
    template_engine = TemplateEngine()

    template_string = "Hello, {{ name }}!"
    result = template_engine.render_from_string(template_string, {"name": "John Doe"})
    assert result == "Hello, John Doe!"

    node = Node(name="John Doe")
    template_string = "Hello, {{ node.name }}!"
    result = template_engine.render_from_string(template_string, {"node": node})
    assert result == "Hello, John Doe!", result


def test__e():
    #
    #
    child1 = Node(description="{{ node.name }}'s child", value="2")
    child2 = Node(name="child2")
    root = Node(name="root", value="1", children=[child1, child2])

    # Initialize the template engine and visitor
    template_engine = TemplateEngine()
    visitor = NodeAttributesRenderereVisitor(template_engine)

    # Traverse the tree and render the templates
    visitor.traverse(root)

    # Print the result
    assert root.children[0].description == "root's child", root.children[0].description


def test__f():
    tpl = "{{ name }}"

    with temporary_files(
        {
            "tpl.j2": tpl,
        }
    ):
        engine = TemplateEngine(template_dir=".")
        ctx = {"name": "santos"}
        from_file = engine.render_from_file("tpl.j2", ctx)
        from_str = engine.render_from_string(tpl, ctx)
        assert from_file == from_str, f"{from_file!r} != {from_str!r}"


def test__g(settings):
    with temporary_files(
        {
            "person.j2": "My name is {{node.name}}.",
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator('<person name="Mauro"></person>')
        res = generator.generate()

    assert res == "My name is Mauro.", res


def test__h(settings):
    with temporary_files(
        {
            "person.j2": "My name is {{node.name}} and I am {{ node.age }} years old.",
            "person.yaml": "- age: 37",
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator('<person name="Mauro"></person>')
        res = generator.generate()

    assert res == "My name is Mauro and I am 37 years old.", res


def test__i(settings):
    with temporary_files(
        {
            "person.j2": "My name is {{ node.name }} and I am {{ node.age }} years old.",
            "person.yaml": "- age: {{ [1, 200, 37]|max }}",
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator('<person name="Mauro"></person>')
        res = generator.generate()

    assert res == "My name is Mauro and I am 200 years old.", res


def test__j(settings):
    with temporary_files(
        {
            "team.j2": (
                """Team {{node.name}}:
{% for child in node.children -%}
    - {{ child.name }}
{% endfor -%}
    """
            ),
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator(
            """
        <team name="B Players">
            <player name="Mauro"></player>
            <player name="Igor"></player>
        </team>
        """
        )
        res = generator.generate()

    expected = """Team B Players:
- Mauro
- Igor
"""
    assert res == expected, f"\n{res!r}\n{expected!r}"


def test__k(settings):
    with temporary_files(
        {
            "team.j2": (
                """Team {{node.name}}:
{% for child in node.children -%}
    {{ render(child) }}
{% endfor -%}
    """
            ),
            "player.j2": "- {{ node.name }}",
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator(
            """
        <team name="B Players">
            <player name="Mauro"></player>
            <player name="Igor"></player>
        </team>
        """
        )
        res = generator.generate()

    expected = """Team B Players:
- Mauro
- Igor
"""
    assert res == expected, f"{res!r} != {expected!r}"


#
#
#
def test__l(settings):
    with temporary_files(
        {
            "country.j2": (
                """Country {{node.name}}:
{% for child in node.children -%}
    {{ render(child) }}
{% endfor -%}"""
            ),
            "team.j2": (
                """Team {{node.name}}:
{% for child in node.children -%}
    {{ render(child) }}
{% endfor -%}"""
            ),
            "player.j2": "- {{ node.name }}",
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator(
            """
        <country name="PyLand">
            <team name="B Team">
                <player name="Mauro"></player>
                <player name="Igor"></player>
            </team>
        </country>
        """
        )
        res = generator.generate()

    expected = """Country PyLand:
Team B Team:
- Mauro
- Igor

"""
    assert res == expected, f"{res!r} != {expected!r}"


#
#
#
def test__m(settings):
    with temporary_files(
        {
            "team.j2": (
                """Team {{node.name}}:
{% for child in node.children -%}
    {{ render(child) }}
{% endfor -%}
    """
            ),
            "player.j2": "- {{ node.name }}",
            "_.j2": (
                """{%- for child in node.children -%}
    {{ render(child) }}
{%- endfor %}"""
            ),
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator(
            """
        <void>
            <team name="a-players" coral-to="{{ node.name }}.txt">
                <player name="Mauro"/>
                <player name="Igor"/>
            </team>
            <team name="b-players" coral-to="{{ node.name }}.txt">
                <player name="Santos"/>
                <player name="Simões"/>
            </team>
        </void>
        """
        )
        res = generator.generate()

    expected = """Team a-players:
- Mauro
- Igor
Team b-players:
- Santos
- Simões
"""
    assert res == expected, f"{res!r} != {expected!r}"


model = (
    "class {{ node.name }}Model(models.Model):\n"
    "    {%- for child in node.children %}\n"
    "    {{ render(child) }}\n"
    "    {%- endfor %}\n"
)

field = "{{ node.name }} = models.{{ node.type | title }}Field()"


def test__n(settings):
    struct = """
        <model name="User">
            <field name="id" type="integer"/>
            <field name="username" type="char"/>
            <field name="email" type="email"/>
        </model>
    """

    with temporary_files(
        {
            "model.j2": model,
            "field.j2": field,
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator(struct)
        result = generator.generate()

    expected = """class UserModel(models.Model):
    id = models.IntegerField()
    username = models.CharField()
    email = models.EmailField()"""

    assert result == expected, f"\n{result!r}\n{expected!r}"


def test__o(settings):
    struct2 = """
    <void>
    <void>
        <model name="User">
            <field name="id" type="integer"/>
            <field name="username" type="char"/>
            <field name="email" type="email"/>
        </model>
    </void>
    </void>"""

    expected = """class UserModel(models.Model):
    id = models.IntegerField()
    username = models.CharField()
    email = models.EmailField()"""

    with temporary_files(
        {
            "model.j2": model,
            "field.j2": field,
        },
        prefix=settings.folder_name,
    ):
        generator = NodeGenerator(struct2)
        result = generator.generate()

    assert result == expected, f"\n{result!r}\n{expected!r}"
