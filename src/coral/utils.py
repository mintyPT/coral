import functools
from pathlib import Path
from typing import Any, Callable


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
