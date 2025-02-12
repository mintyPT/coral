from contextlib import contextmanager

import pytest


@pytest.fixture
def temporary_files(tmp_path):
    """
    Creates temporary files based on a dictionary mapping filenames to file content.
    Returns a context manager that creates the files in a temporary directory and adds
    that directory to sys.path.
    """

    @contextmanager
    def _create(files, prefix=""):
        # Create a base directory in tmp_path with an optional prefix.
        base_dir = tmp_path / prefix if prefix else tmp_path
        base_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            file_path = base_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            print(f"Created {file_path}")
        yield base_dir

    return _create


@pytest.fixture
def settings():
    """
    Provides a simple settings object with a 'folder_name' attribute.
    """

    class Settings:
        folder_name = "temp_folder"  # You can adjust the folder name as needed.

    return Settings()
