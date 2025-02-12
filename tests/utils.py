import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional



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
