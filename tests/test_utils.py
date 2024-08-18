from coral.utils import apply_functions, flatten


def test__flatten():
    assert flatten([[1, 2, 3], [4, 5, 6]]) == [1, 2, 3, 4, 5, 6]


def test__apply_functions():
    assert apply_functions([], 3) == 3
    assert apply_functions([str], 3) == "3"
