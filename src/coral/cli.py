import logging
from pathlib import Path

import click

from . import NodeGenerator, Settings
from .utils import read_file

# Add version constant at the top
__version__ = "0.1.0"


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def cli(verbose: bool):
    """
    Coral - A template-based code generator.
    """
    ctx = click.get_current_context()
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.pass_context
def version(ctx):
    """Show the version and exit."""
    click.echo(f"Coral v{__version__}")


@cli.command()
@click.option(
    "--model",
    "-m",
    type=click.Path(exists=True),
    default=".coral/model.xml",
    help="Path to the XML model file (default: .coral/model.xml)",
)
@click.option(
    "--root-dir",
    "-r",
    type=click.Path(exists=True),
    default=".",
    help="Root directory for templates and configuration (default: current directory)",
)
@click.option(
    "--template-dir",
    "-t",
    type=str,
    default="templates",
    help="Template directory (default: .coral/templates)",
)
@click.pass_context
def generate(ctx, model: str, root_dir: str, template_dir: str):
    """Generate code from templates using the model file."""
    try:
        model_content = read_file(Path(model))
        generator = NodeGenerator(
            xml_input=model_content,
            root_dir=root_dir,
            template_folder_name=template_dir,
            settings=Settings(),
        )
        generator.generate()
    except Exception as e:
        if ctx.obj["verbose"]:
            import traceback

            traceback.print_exc()
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli(obj={})
