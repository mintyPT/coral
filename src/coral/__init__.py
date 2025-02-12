import json
import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, List, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .utils import (apply_functions, flatten, iter_tree, map_func, remove_dups,
                    write_to_file)


class Settings:
    def __init__(self, folder_name=None):
        self.folder_name = folder_name or os.getenv("CORAL_FOLDER_NAME", ".coral")

    @property
    def template_folder(self):
        return f"{self.folder_name}/templates"


def prepare_paths(settings: Settings, paths: list[str]) -> list[Path]:
    """
    Prepare a list of paths by resolving them and adding the settings folder name.
    This will return the list of all places where models and templates can be found.

    This function takes a list of paths and:
    1. Resolves each path to its absolute form
    2. Generates parent paths for each path
    3. Flattens the resulting list of paths
    4. Removes any duplicate paths
    5. Appends the settings folder name to each path

    Args:
        settings: Settings object containing the folder_name to append
        paths: List of path strings to process

    Returns:
        List of Path objects with settings folder name appended

    Example:
        >>> settings = Settings(folder_name='.coral')
        >>> prepare_paths(settings, ['/a/b/c', '/d/e'])
        [
            Path('/a/b/c/.coral'),
            Path('/a/b/.coral'),
            Path('/a/.coral'),
            Path('/.coral'),
            Path('/d/e/.coral'),
            Path('/d/.coral')
        ]
    """
    return apply_functions(
        [
            # Resolve the path to its absolute form
            map_func(lambda path: Path(path).resolve()),
            # Generate parent paths
            map_func(iter_tree),
            # Flatten the resulting list of paths
            flatten,
            # Remove any duplicate paths
            remove_dups,
            # Append the settings folder name to each path
            map_func(lambda path: path / settings.folder_name),
            # Sort the paths
            lambda paths: sorted(
                paths, key=lambda path: len(list(iter_tree(path))), reverse=True
            ),
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
        attrs_str = ", ".join(
            f"{k}={v!r}" for k, v in self.attributes.items() if k not in ["tag"]
        )
        if attrs_str:
            attrs_str = f"({attrs_str})"
        tag = self.tag or "Node"
        return f"{indent}<{tag} {attrs_str}>" + (f"\n{child_str}" if child_str else "")


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
        attributes = {}
        for key, value in element.attrib.items():
            try:
                attributes[key] = json.loads(value)
            except json.JSONDecodeError:
                attributes[key] = value
        attributes["tag"] = element.tag
        return Node(**attributes, children=children)

    def build_from_file(self, filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()
        return self.build(root)


class TemplateEngine:
    def __init__(self, template_dir=None):
        if template_dir:
            self.env = Environment(
                loader=FileSystemLoader(template_dir), undefined=StrictUndefined
            )
        else:
            self.env = Environment(undefined=StrictUndefined)

    def render_from_file(self, template_file, context):
        template = self.env.get_template(template_file)
        return template.render(context)

    def render_from_string(self, template_string, context):
        template = self.env.from_string(template_string)
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
    def __init__(self, directories=[Path(".")], template_engine=None):
        # Ensure all directories are Path objects
        self.directories = [Path(directory) for directory in directories]
        # Use the provided template engine or create a new one if not provided
        self.template_engine = template_engine or TemplateEngine()

    def visit(self, node):
        for directory in self.directories:
            yaml_file = directory / f"{node.tag}.yaml"
            if yaml_file.exists():
                with yaml_file.open("r") as file:
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


def log_all(func):
    def wrapper(*args, **kwargs):
        print(f"👉 Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        print(f"👉 {func.__name__} returned: {result}")
        return result

    return wrapper


def load_hooks_from_file(hook_file: Path) -> List[Callable[["Node"], None]]:
    """Load pre-render hooks from the given hook file."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("coral_hooks", str(hook_file))
    if spec is None:
        raise ImportError(f"Could not load module from {hook_file}")
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"No loader for module from {hook_file}")
    spec.loader.exec_module(module)
    return getattr(module, "pre_render_hooks", [])


class NodeGenerator:
    def __init__(
        self,
        xml_input,
        root_dir=".",
        templates=None,
        settings=None,
        template_folder_name=None,
        pre_render_hooks: Optional[List[Callable[["Node"], None]]] = None,
        hooks_file_name: str = "hooks.py",
    ):
        self.settings = settings or Settings()

        template_dirs = prepare_paths(self.settings, root_dir)
        if template_folder_name:
            template_dirs = [p / template_folder_name for p in template_dirs]

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
        self.templates["void"] = """{%- for child in node.children -%}
    {{ render(child) }}
{%- endfor %}"""
        self.pre_render_hooks = pre_render_hooks or []
        # Auto-load hooks from a single hooks file: look for hooks_file_name
        # in the prepared paths and load the first one found.
        hook_dirs = prepare_paths(self.settings, root_dir)
        for hook_dir in hook_dirs:
            hook_file = hook_dir / hooks_file_name
            if hook_file.exists():
                self.pre_render_hooks.extend(load_hooks_from_file(hook_file))

    def register_pre_render_hook(self, hook: Callable[["Node"], None]) -> None:
        """Register a pre-render hook to modify/process nodes before rendering."""
        self.pre_render_hooks.append(hook)

    def _build_node(self):
        root_element = ET.fromstring(self.xml_input)
        return self.xml_builder.build(root_element)

    def _apply_pre_render_hooks_recursively(self, node):
        """
        Recursively apply pre-render hooks to a node and its children.
        """
        if not getattr(node, "_pre_render_hook_applied", False):
            for hook in self.pre_render_hooks:
                hook(node)
            node._pre_render_hook_applied = True
        for child in node.children:
            self._apply_pre_render_hooks_recursively(child)

    def _render(self, node):
        logging.debug(f"Rendering node:\n{node}\n")

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
            write_to_file(output_path, ret)
            logging.info(f"Saved to {output_path}")

        if "coral-print" in node.attributes:
            print(ret)

        return ret

    def generate(self):
        # Preprocess the entire node tree with hooks before rendering.
        self._apply_pre_render_hooks_recursively(self.node)
        ret = self._render(self.node)
        return ret
