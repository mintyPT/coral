import click
from pathlib import Path
from .utils import read_file
from . import NodeGenerator, Settings

@click.command()
@click.option(
    '--model', '-m',
    type=click.Path(exists=True),
    default='.coral/model.xml',
    help='Path to the XML model file (default: .coral/model.xml)'
)
@click.option(
    '--root-dir', '-r',
    type=click.Path(exists=True),
    default='.',
    help='Root directory for templates and configuration (default: current directory)'
)
@click.option(
    '--template-dir', '-t',
    type=str,
    default='templates',
    help='Template directory (default: .coral/templates)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def cli(model: str, root_dir: str, template_dir: str, verbose: bool):
    """
    Coral - A template-based code generator.
    
    By default, looks for a model file at .coral/model.xml in the current directory.
    """
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        model_content = read_file(Path(model))
        generator = NodeGenerator(
            xml_input=model_content,
            root_dir=root_dir,
            template_folder_name=template_dir,
            settings=Settings()
        )
        generator.generate()
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli() 