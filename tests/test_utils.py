from pathlib import Path
from src.coral.utils import apply_functions, flatten, iter_tree, map_func, remove_dups


def test__flatten():
    assert flatten([[1, 2, 3], [4, 5, 6]]) == [1, 2, 3, 4, 5, 6]


def test__apply_functions():
    assert apply_functions([], 3) == 3
    assert apply_functions([str], 3) == "3"


def test__iter_tree():
    assert list(iter_tree(Path("/a/b/c"))) == [
        Path("/a/b/c"),
        Path("/a/b"),
        Path("/a"),
        Path("/"),
    ], list(iter_tree(Path("/a/b/c").resolve()))


def test__map_func():
    assert list(map_func(lambda n: n * 2)([1, 2, 3])) == [2, 4, 6]


def test__remove_dups():
    assert remove_dups([1, 2, 3, 1, 2, 3]) == [1, 2, 3]
