import functools
from typing import TypeVar
from pathlib import Path
from typing import Any, Callable
from typing import Generator


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


def apply_functions(functions: list[Callable[[Any], Any]], initial_value: Any) -> Any:
    """
    Applies a list of functions sequentially to an initial value.

    This function takes a list of functions and an initial value. It applies
    each function in the list to the result of the previous function, starting
    with the initial value, and returns the final result.

    :param functions: A list of functions to be applied sequentially. Each function
                      must take one argument and return a value of the same type.
    :param initial_value: The initial value to be transformed by the functions.
    :return: The final result after all functions have been applied.

    Example:
    >>> def add_one(x: int) -> int:
    >>>     return x + 1
    >>>
    >>> def multiply_by_two(x: int) -> int:
    >>>     return x * 2
    >>>
    >>> apply_functions([add_one, multiply_by_two], 5)
    12
    """
    return functools.reduce(lambda value, func: func(value), functions, initial_value)


T = TypeVar("T")
U = TypeVar("U")


def remove_dups(arr: list[T]) -> list[T]:
    """
    Removes duplicates from the input list while preserving the original order.

    :param arr: A list that may contain duplicate elements.
    :return: A list with duplicates removed, maintaining the original order of elements.

    Example:
    >>> remove_dups([1, 2, 3, 2, 1])
    [1, 2, 3]
    """
    ret = []
    for a in arr:
        if a not in ret:
            ret.append(a)
    return ret


def iter_tree(path: Path) -> Generator[Path, None, None]:
    """
    Iteratively yields a path and all its parent directories up to the root.

    :param path: A file or directory path.
    :yield: The input path and each of its parent directories, starting from the input path itself.

    Example:
    >>> list(iter_tree(Path("/a/b/c")))
    [PosixPath('/a/b/c'), PosixPath('/a/b'), PosixPath('/a'), PosixPath('/')]
    """
    yield path
    if path.parent and path.parent != path:
        yield from iter_tree(path.parent)


def map_func(func: Callable[[T], U]) -> Callable[[list[T]], list[U]]:
    """
    Returns a function that applies the provided function to each element of a list.

    :param func: A function that takes an element of type T and returns a result of type U.
    :return: A function that takes a list of elements of type T and returns a list of elements of type U.

    Example:
    >>> multiply_by_two = map_func(lambda x: x * 2)
    >>> multiply_by_two([1, 2, 3])
    [2, 4, 6]
    """
    return lambda arr: list(map(func, arr))
