"""Functional tests for looping-through-iterator checker."""

# pylint: disable=missing-docstring,import-outside-toplevel,unused-variable,
# pylint: disable=unnecessary-comprehension,too-few-public-methods, trailing-whitespace


def generator_expression_global_scope():
    gen_ex = (x for x in range(3))
    for _i in range(2):
        for item in gen_ex:  # [looping-through-iterator]
            print(item)


def map_object_global_scope():
    map_obj = map(str, range(3))
    for _i in range(2):
        for item in map_obj:  # [looping-through-iterator]
            print(item)


def filter_object_global_scope():
    filter_obj = filter(None, range(3))
    for _i in range(2):
        for item in filter_obj:  # [looping-through-iterator]
            print(item)


def zip_object_global_scope():
    zip_obj = zip(range(3), "abc")
    for _i in range(2):
        for item in zip_obj:  # [looping-through-iterator]
            print(item)


def iter_object_global_scope():
    my_list = [1, 2, 3]
    iter_obj = iter(my_list)
    for _i in range(2):
        for item in iter_obj:  # [looping-through-iterator]
            print(item)


def iter_callable_sentinel_global_scope():
    from itertools import count

    counter = count(0)

    def get_next():
        return next(counter)

    iter_call_obj = iter(get_next, 3)
    for _i in range(2):
        for item in iter_call_obj:  # [looping-through-iterator]
            print(item)


def nested_consuming_producing_calls():
    import string

    iter1 = map(lambda x: x, string.printable)
    iter2 = set(map(lambda x: x, string.printable))
    for i in range(5):
        for i1, i2 in list(zip(iter1, iter2)): # [looping-through-iterator]
            # iter1 is an iterator produced once and reused here.
            print(i, i1, i2)  


def reversed_object_global_scope():
    my_tuple = (1, 2, 3)
    rev_obj = reversed(my_tuple)
    for _i in range(2):
        for item in rev_obj:  # [looping-through-iterator]
            print(item)


def iterator_defined_in_func_before_outer_loop():
    def func():
        gen_ex = (x for x in range(3))
        for _i in range(2):
            for item in gen_ex:  # [looping-through-iterator]
                print(item)

    func()


def multiple_levels_of_nesting():
    gen_ex = (x for x in range(3))
    for _i in range(2):
        for _j in range(2):
            for item in gen_ex:  # [looping-through-iterator]
                print(item)


def nested_consumer_producer_calls():
    iter1 = map(lambda x: x, range(5))
    for i in filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))):
        for j, k in zip(iter1, iter(range(5))): # [looping-through-iterator]
            print("i ", i, "j ", j, "k ", k)  

def iterator_stolen_by_nested_while_loop():
    data_iterator = iter(range(20))  # Defined once, outside all loops
    for i in range(5):
        item = next(data_iterator)
        print(f"Outer loop got: {item}")
        while item < 10:
            item = next(data_iterator)  # [looping-through-iterator]
            print(f"  Inner loop got: {item}")
            if item % 3 == 0:
                break


def no_warning_if_iterator_defined_inside_outer_loop():
    def my_func():
        for _i in range(2):
            gen_ex_inner = (x for x in range(3))
            for item in gen_ex_inner:
                print(item)

    my_func()


def no_warning_for_list_comprehension_or_list_literal():
    my_list_comp = [x for x in range(3)]
    my_list_lit = [1, 2, 3]
    for _i in range(2):
        for item in my_list_comp:
            print(item)
        for item_lit in my_list_lit:
            print(item_lit)


def no_warning_if_iterator_converted_to_set():
    gen_ex = (x for x in range(3))
    list_from_gen = set(map(list, gen_ex))
    for _i in range(2):
        for item in list_from_gen:
            print(item)


def no_warning_for_single_loop():
    gen_ex = (x for x in range(3))
    for item in gen_ex:
        print(item)


def no_warning_for_range_object():
    range_obj = range(3)
    for _i in range(2):
        for item in range_obj:
            print(item)


def no_warning_if_iterator_shadowed_in_outer_loop_list():
    it = (x for x in range(3))
    for i in range(2):
        it = [10, 20, 30]
        for item in it:
            print(i, item)


def no_warning_if_iterator_shadowed_in_outer_loop_generator():
    it = (x for x in range(3))
    for i in range(2):
        it = (i + y for y in range(1))
        for item in it:
            print(i, item)


def no_warning_when_assign_target_is_not_simple_name():
    class MyClass:
        def __init__(self):
            self.my_iter = (x for x in range(3))

        def run(self):
            for i in range(2):
                for item in self.my_iter:
                    print(i, item)

    MyClass().run()


def no_warning_for_comprehension_directly_in_for_loop():
    my_data = [1, 2, 3]
    for i in range(2):
        for item in (x * i for x in my_data):
            print(item)


def re_initialized_iterator_in_outer_loop_no_warn():
    for _i in range(2):
        my_iter = (x for x in range(3))
        for item in my_iter:
            print(item)


def iterator_consumed_once_per_outer_loop_no_warn():
    outer_data = range(2)
    for outer_item in outer_data:
        my_gen = (x for x in range(outer_item, outer_item + 2))
        for item in my_gen:
            print(item)


def iterator_name_reassigned_to_non_iterator_no_warn():
    my_iter = map(str, range(3))
    my_iter = [1, 2, 3]
    for _i in range(2):
        for item in my_iter:
            print(item)


def non_iterator_overwrites_iter_name_no_warn():
    my_iter = map(str, range(3))
    my_iter = [1, 2, 3]
    for _i in range(2):
        for item in my_iter:
            print(item)


def iterator_used_inner_loop_called_outer_loop():
    def get_numbers_iterator(start):
        return (x for x in range(start, start + 3))

    for i in range(2):
        numbers_iter = get_numbers_iterator(i)
        for num in numbers_iter:
            print(num)


def iterator_consumed_once_per_outer_loop_top_level():
    outer_data = range(2)
    for outer_item in outer_data:
        my_gen = (x for x in range(outer_item, outer_item + 2))
        for item in my_gen:
            print(item)


def list_call_in_loop_no_warning():
    for i in range(5):
        iterator1 = (j for j in [1, 2, 3])
        for j in list(iterator1):
            print("i ", i, "j ", j)


def nested_call_in_loop_no_warning():
    iter1 = map(lambda x: x, list(i for i in [1, 2, 3, 4, 5]))
    iter2 = set(map(lambda x: x, list(i for i in [1, 2, 3, 4, 5])))
    for i1, i2 in zip(iter1, iter2):
        for i in range(5):
            print(i1, i2, i)


def reassign_in_inner_loop_no_warning():
    iter1 = map(lambda x: x, range(5))
    for i in filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))):
        iter1 = map(lambda x: x, range(5))
        for j, k in zip(iter1, iter(range(5))):
            print("i ", i, "j ", j, "k ", k)


def iterator_reinitialized_in_outer_loop_is_safe():
    for i in range(2):
        data = [10, 20, 30, 40]
        my_iter = iter(data)
        for j in range(2):
            print(i, j, next(my_iter))


def iterator_in_deeply_nested_loop_is_safe():
    for i in range(2):
        my_iter = iter([10, 20])
        for j in range(2):
            print(f"j={j}")
            for item in my_iter:
                print(f"  i={i}, item={item}")


def iterator_reinitialized_in_loop_no_warning():
    responses = {"a": [1, 2], "b": [3, 4]}
    for source, results in responses.items():
        results_iter = iter(results)
        for i in range(2):
            item = next(results_iter)
            print(source, i, item)


def no_warning_gen_producer_call_directly_in_loop():
    my_list = [1, 2, 3]
    for _i in range(4):
        for item in map(lambda x: x, my_list):
            print(item)
