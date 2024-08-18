from typing import Any


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
