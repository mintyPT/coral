import os
import os
from typing import Any, Generator, Optional
import yaml
import json
import logging
import functools
from pathlib import Path
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pprint import pprint
import functools
from jinja2 import (
    FileSystemLoader,
    TemplateNotFound,
    Environment,
    FileSystemLoader,
    Template,
)
import logging as logging_

import logging
import sys


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


def flatten(arr: list[list[Any]]) -> list[Any]:
    """
    Flattens a list of lists into a single list.

    :param arr: A list of lists to be flattened.
    :return: A single list containing all the elements of the nested lists.

    Example:
    >>> flatten([[1, 2], [3, 4], [5]])
    [1, 2, 3, 4, 5]
    """
    return [element for subarr in arr for element in subarr]


def apply_functions(functions, initial_value):
    return functools.reduce(lambda value, func: func(value), functions, initial_value)


def remove_dups(arr):
    ret = []
    for a in arr:
        if a not in ret:
            ret.append(a)
    return ret


def iter_tree(path: Path):
    yield path
    if path.parent and path.parent != path:
        yield from iter_tree(path.parent)


def map_func(func):
    return lambda arr: list(map(func, arr))


class Settings:
    def __init__(self, folder_name=".coral"):
        self.folder_name = folder_name

    @property
    def template_folder(self):
        return f"{self.folder_name}/templates"


def prepare_paths(settings, paths):
    return apply_functions(
        [
            map_func(lambda path: Path(path).resolve()),
            map_func(iter_tree),
            flatten,
            remove_dups,
            map_func(lambda path: path / settings.folder_name),
        ],
        paths,
    )


class Node:
    def __init__(self, **attributes):
        self.attributes = attributes
        self.children = attributes.pop("children", [])
        for child in self.children:
            child.parent = self
        self.parent = None

    def __getattr__(self, attr):
        if attr in self.attributes:
            return self.attributes[attr]
        elif self.parent:
            return getattr(self.parent, attr)
        else:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{attr}'"
            )

    def __str__(self, level=0):
        indent = "    " * level
        child_str = "\n".join([child.__str__(level + 1) for child in self.children])
        attrs_str = ", ".join(f"{k}={v}" for k, v in self.attributes.items())
        return f"{indent}Node({attrs_str})" + f"\n{child_str}" if child_str else f""


class JsonNodeBuilder:
    def build(self, data):
        if isinstance(data, dict):
            attributes = {k: v for k, v in data.items() if k != "children"}
            children = [self.build(child) for child in data.get("children", [])]
            return Node(**attributes, children=children)
        return None

    def build_from_file(self, filepath):
        with open(filepath, "r") as file:
            data = json.load(file)
            return self.build(data)


class NodeVisitor:
    def visit(self, node):
        raise NotImplementedError("You should implement this method!")

    def traverse(self, node):
        self.visit(node)
        for child in node.children:
            self.traverse(child)


class CompositeNodeVisitor:
    def __init__(self, visitors):
        self.visitors = visitors

    def traverse(self, node):
        for visitor in self.visitors:
            visitor.traverse(node)


class PrintNodeVisitor(NodeVisitor):
    def visit(self, node):
        print(node)


class JsonNodeBuilder:
    def build(self, data):
        if isinstance(data, dict):
            attributes = {k: v for k, v in data.items() if k != "children"}
            children = [self.build(child) for child in data.get("children", [])]
            return Node(**attributes, children=children)
        return None

    def build_from_file(self, filepath):
        with open(filepath, "r") as file:
            data = json.load(file)
            return self.build(data)


class XmlNodeBuilder:
    def build(self, element):
        children = [self.build(child) for child in element]
        attributes = {
            **element.attrib,
            "tag": element.tag,
            "text": element.text.strip() if element.text else "",
        }
        return Node(**attributes, children=children)

    def build_from_file(self, filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()
        return self.build(root)


class TemplateEngine:
    def __init__(self, template_dir=None):
        if template_dir:
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.env = Environment()

    def render_from_file(self, template_file, context):
        template = self.env.get_template(template_file)
        return template.render(context)

    def render_from_string(self, template_string, context):
        template = Template(template_string)
        ret = template.render(context)
        return ret


class NodeAttributesRenderereVisitor(NodeVisitor):
    def __init__(self, template_engine):
        self.template_engine = template_engine

    def visit(self, node):
        for attr, value in node.attributes.items():
            if isinstance(value, str):
                rendered_value = self.template_engine.render_from_string(
                    value, {"node": node}
                )
                node.attributes[attr] = rendered_value


class YamlAttributeVisitor(NodeVisitor):
    def __init__(self, directories=["."], template_engine=None):
        self.directories = directories
        # Use the provided template engine or create a new one if not provided
        self.template_engine = template_engine or TemplateEngine()

    def visit(self, node):
        for directory in self.directories:
            yaml_file = os.path.join(directory, f"{node.tag}.yaml")
            if os.path.exists(yaml_file):
                with open(yaml_file, "r") as file:
                    # Render the YAML content first
                    raw_yaml_content = file.read()
                    rendered_yaml_content = self.template_engine.render_from_string(
                        raw_yaml_content, {"node": node}
                    )

                    # Load the rendered YAML content
                    yaml_data = yaml.safe_load(rendered_yaml_content)

                    if yaml_data:
                        for attributes in yaml_data:
                            node.attributes.update(attributes)
                break


class NodeGenerator:

    def __init__(self, xml_input, root_dir=".", templates=None, settings=None):
        self.settings = settings or Settings()

        template_dirs = prepare_paths(self.settings, root_dir)

        self.xml_input = xml_input

        self.template_engine = TemplateEngine(template_dirs)
        self.template_visitor = CompositeNodeVisitor(
            [
                NodeAttributesRenderereVisitor(self.template_engine),
                YamlAttributeVisitor(
                    directories=template_dirs, template_engine=self.template_engine
                ),
            ]
        )
        self.xml_builder = XmlNodeBuilder()
        self.node = self._build_node()

        self.template_visitor.traverse(self.node)

        self.templates = templates or {}
        self.templates[
            "void"
        ] = """{%- for child in node.children -%}
    {{ render(child) }}
{%- endfor %}"""

    def _build_node(self):
        root_element = ET.fromstring(self.xml_input)
        return self.xml_builder.build(root_element)

    def _render(self, node):

        ctx = {"node": node, "render": self._render}

        template_content = self.templates.get(node.tag)

        from_templates = template_content is not None
        if from_templates:
            ret = self.template_engine.render_from_string(template_content, ctx)
        else:
            ret = self.template_engine.render_from_file(f"{node.tag}.j2", ctx)

        # TODO protect override unless we pass a param
        if "coral-to" in node.attributes:
            output_path = Path(node.attributes["coral-to"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(ret)
            print(f"Saved to {output_path}")

        return ret

    def generate(self):
        ret = self._render(self.node)
        return ret


# test

# import nbformat

# from IPython.display import display, Javascript

# def copy_to_clipboard(text):
#     js_code = f"""
#     navigator.clipboard.writeText(`{text}`).then(function() {{
#         console.log('Text copied to clipboard');
#     }}, function(err) {{
#         console.error('Could not copy text: ', err);
#     }});
#     """
#     display(Javascript(js_code))


# def copy_all_cells(notebook_path):
#     # Load the notebook
#     with open(notebook_path, 'r', encoding='utf-8') as f:
#         notebook = nbformat.read(f, as_version=4)

#     # Copy all cells
#     cells_copy = notebook.cells.copy()

#     return cells_copy

# # Example usage
# notebook_path = 'node.ipynb'
# all_cells = copy_all_cells(notebook_path)


# code = ""
# for cell in all_cells:
#     if not cell['source'].startswith(("# test", )) and cell['cell_type'] == 'code':
#         code += " "
#         code += cell['source']

# # Example usage
# text_to_copy = code
# copy_to_clipboard(text_to_copy)
