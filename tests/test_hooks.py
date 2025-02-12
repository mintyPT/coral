from src.coral import Node, NodeGenerator


def test_pre_render_hook_single():
    # Test that a hook function modifies a node before rendering.
    xml_input = '<hooktest name="Original"/>'
    templates = {"hooktest": "Name: {{ node.name }}"}

    # Define a hook that changes the 'name' attribute for hooktest nodes.
    def hook_change_name(node: Node):
        if node.tag == "hooktest":
            node.attributes["name"] = "HookedName"

    generator = NodeGenerator(
        xml_input,
        templates=templates,
        pre_render_hooks=[hook_change_name],
    )
    result = generator.generate()
    assert result == "Name: HookedName"


def test_pre_render_hook_recursion():
    # Test that the hook is applied to all nodes in a composite tree.
    xml_input = """
    <parent name="Parent">
        <child name="Child1"/>
        <child name="Child2"/>
    </parent>
    """
    parent_tpl = """Parent: {{ node.name }}
{% for child in node.children %}
{{ render(child) }}
{% endfor %}"""
    child_tpl = "Child: {{ node.name }}"
    templates = {"parent": parent_tpl, "child": child_tpl}

    def hook_append_suffix(node: Node):
        # Append '_Processed' to the name of every node.
        node.attributes["name"] = node.name + "_Processed"

    generator = NodeGenerator(
        xml_input,
        templates=templates,
        pre_render_hooks=[hook_append_suffix],
    )
    result = generator.generate()
    expected = """Parent: Parent_Processed
Child: Child1_Processed
Child: Child2_Processed"""
    # Remove extra whitespace and newlines for a clean comparison.
    result = "\n".join([line.strip() for line in result.splitlines() if line.strip()])
    expected = "\n".join(
        [line.strip() for line in expected.splitlines() if line.strip()]
    )
    assert result == expected


def test_register_hook_method():
    # Test that a hook registered via register_pre_render_hook changes the output.
    xml_input = '<hooktest name="Original"/>'
    templates = {"hooktest": "Name: {{ node.name }}"}

    generator = NodeGenerator(xml_input, templates=templates)

    # Register a hook that converts the name value to upper case.
    def hook_upper(node: Node):
        node.attributes["name"] = node.name.upper()

    generator.register_pre_render_hook(hook_upper)
    result = generator.generate()
    assert result == "Name: ORIGINAL"


def test_hooks_loaded_from_file(temporary_files, settings):
    # Test that hooks defined in .coral/hooks.py are auto-loaded and applied.
    xml_input = '<hooktest name="Original"/>'
    templates = {"hooktest": "Name: {{ node.name }}"}
    hooks_file_content = (
        "pre_render_hooks = ["
        "    lambda node: node.attributes.update({'name': node.name + '_File'})"
        "]"
    )

    with temporary_files({"hooks.py": hooks_file_content}, prefix=settings.folder_name):
        generator = NodeGenerator(xml_input, templates=templates)
        result = generator.generate()
        assert result == "Name: Original_File"
