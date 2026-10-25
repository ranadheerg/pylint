"""Emit a message when a counter initialized before a for loop is manually
incremented in its body, instead of using ``enumerate``.
"""

# pylint: disable=missing-docstring, consider-using-enumerate

ITEMS = [1, 2, 3, "4"]


# Positive cases

def increment_first():
    i = 0
    all_possible_cases = [1, 2, 3, "4"]
    for case in all_possible_cases:  # [consider-using-enumerate-counter]
        i += 1
        print(i, case)


def increment_last():
    i = 0
    for case in ITEMS:  # [consider-using-enumerate-counter]
        print(i, case)
        i += 1


def increment_with_binop():
    i = 0
    for case in ITEMS:  # [consider-using-enumerate-counter]
        i = i + 1
        print(i, case)


def increment_with_reversed_binop():
    i = 0
    for case in ITEMS:  # [consider-using-enumerate-counter]
        print(i, case)
        i = 1 + i


def non_zero_start():
    i = 10
    for case in ITEMS:  # [consider-using-enumerate-counter]
        print(i, case)
        i += 1


def tuple_target():
    i = 0
    for key, value in {"a": 1}.items():  # [consider-using-enumerate-counter]
        i += 1
        print(i, key, value)


def continue_with_increment_first():
    i = 0
    for case in ITEMS:  # [consider-using-enumerate-counter]
        i += 1
        if case == 2:
            continue
        print(i, case)


def break_with_increment_first():
    i = 0
    for case in ITEMS:  # [consider-using-enumerate-counter]
        i += 1
        if case == 2:
            break
        print(i, case)


def continue_in_nested_loop_with_increment_last():
    i = 0
    for case in ITEMS:  # [consider-using-enumerate-counter]
        for char in str(case):
            if char == "2":
                continue
        print(i, case)
        i += 1


def statement_between_unrelated():
    i = 0
    other = 5
    for case in ITEMS:  # [consider-using-enumerate-counter]
        i += 1
        print(i, case, other)


j = 0
for module_case in ITEMS:  # [consider-using-enumerate-counter]
    print(j, module_case)
    j += 1


# Negative cases

def continue_with_increment_last():
    i = 0
    for case in ITEMS:
        if case == 2:
            continue
        print(i, case)
        i += 1


def conditional_increment():
    i = 0
    for case in ITEMS:
        if case == 2:
            i += 1
        print(i, case)


def increment_in_middle():
    i = 0
    for case in ITEMS:
        print(i)
        i += 1
        print(i, case)


def increment_by_two():
    i = 0
    for case in ITEMS:
        i += 2
        print(i, case)


def decrement():
    i = 0
    for case in ITEMS:
        i -= 1
        print(i, case)


def used_after_loop():
    i = 0
    for case in ITEMS:
        i += 1
        print(case)
    return i


def used_in_else():
    i = 0
    for case in ITEMS:
        i += 1
        if case == 2:
            break
    else:
        print(i)


def reassigned_in_body():
    i = 0
    for case in ITEMS:
        i += 1
        if case == 2:
            i = 0
        print(i, case)


def walrus_in_body():
    i = 0
    for case in ITEMS:
        i += 1
        if (i := i * 2) > 4:
            print(case)


def used_by_closure():
    i = 0

    def show():
        print(i)

    for case in ITEMS:
        i += 1
        show()
        print(case)


def counter_is_nonlocal():
    i = 0

    def inner():
        nonlocal i
        for case in ITEMS:
            i += 1
            print(i, case)

    inner()


def counter_used_between():
    i = 0
    print(i)
    for case in ITEMS:
        i += 1
        print(case)


def counter_modified_between():
    i = 0
    i += 5
    for case in ITEMS:
        i += 1
        print(i, case)


def bool_initializer():
    i = False
    for case in ITEMS:
        i += 1
        print(i, case)


def float_initializer():
    i = 0.0
    for case in ITEMS:
        i += 1
        print(i, case)


def multiple_targets():
    i = k = 0
    for case in ITEMS:
        i += 1
        print(i, k, case)


def counter_is_loop_target():
    i = 0
    for i in ITEMS:
        i += 1
        print(i)


def nested_loop_increment():
    i = 0
    for case in ITEMS:
        for char in str(case):
            i += 1
            print(i, char)


def two_increments():
    i = 0
    for case in ITEMS:
        i += 1
        print(i, case)
        i += 1


def range_len_pattern():
    for idx in range(len(ITEMS)):
        print(idx, ITEMS[idx])


async def async_for(aiterable):
    i = 0
    async for case in aiterable:
        i += 1
        print(i, case)


def initializer_not_directly_before_loop(flag):
    i = 0
    if flag:
        for case in ITEMS:
            i += 1
            print(i, case)
