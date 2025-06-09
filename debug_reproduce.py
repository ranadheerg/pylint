# iter1 = map(lambda x: x, list(i for i in [1,2,3,4,5]))
# iter2 = set(map(lambda x: x, list(i for i in [1,2,3,4,5])))
# for i in range(5):
#     for i1, i2 in list(zip(iter1,iter2)):
#         print(i1, i2)

# for i1, i2 in zip(iter1, iter2):
#     for i in range(5):
#         print(i1, i2, i)
# iter1 = (x for x in [1, 2, 3, 4, 5])
#
# for i in range(5):
#     for i1 in iter1:
#         print(i, i1)

# data = [1, 2, 3]
# my_iter = iter(data)
# # 'iter' is in KNOWN_ITERATOR_PRODUCING_FUNCTIONS
# for _i in range(2):
#     for i in range(3):
#         print("a")
#     for item in my_iter:
#         print(item)
#
# # Iterator is defined once, outside the loop
# data_iterator = map(str, range(10))
#
# # An outer loop that will run multiple times
# for i in range(5):
#     print(f"Outer iteration #{i}")
#
#     # The iterator is consumed by a function call INSIDE THE LOOP BODY.
#     # On iteration i=0, this will be ['0', '1', ...].
#     # On iteration i=1, data_iterator is already empty, so this will be [].
#     current_data = zip(filter(lambda x: x != 2, data_iterator), data_iterator)  # <-- visit_call finds this!
#
#     print(current_data)
#

# import astroid
#
# from pylint import interfaces
# #from pylint.checkers.looping_iterator_checker import RepeatedIteratorLoopChecker
# from pylint.testutils import CheckerTestCase, MessageTest

"""test 1 calling iterator in for loop """
# for spam in range(10):
#     iterator = (ord(x) for x in "abc")
#     for spam2 in range(10):
#         for eggs in iterator:# this won't work as expected and is really hard to catch!
#             print("spam ", spam)
#             print("spam2 ", spam2)
#             print("eggs ", eggs)
#             print(chr(spam*eggs))

# gen_ex = (x for x in range(3))
# for _i in range(2):
#     for item in gen_ex:
#         print(item)

"""test 2 calling map operator in for loop """
# iterator = filter(lambda x: ord(x) == 98, "abc")
# for spam in range(10):
#     for eggs in iterator:# this won't work as expected and is really hard to catch!
#         # print("spam ", spam)
#         # print("eggs ", eggs)
#         print(chr(spam*ord(eggs)))

"""test 3 calling filter operator in for loop"""
# iterator = map(lambda x: ord(x), filter(lambda x: ord(x) == 98, "abc"))
# for spam in range(10):
#     for eggs in iterator:# this won't work as expected and is really hard to catch!
#         # print("spam ", spam)
#         # print("eggs ", eggs)
#         print(chr(spam*eggs))

"""test 4 calling zip in for loop"""
# l1 = [1, 2, 3]
# l2 = ['a', 'b', 'c']
#
# iterator = zip(l1, l2)
# for spam in range(10):
#     for l1_item, l2_item in iterator:# this won't work as expected and is really hard to catch!
#         # print("spam ", spam)
#         # print("eggs ", eggs)
#         print(chr(spam+l1_item), chr(spam)+l2_item)

"""test 5 calling range function"""

# iterator = range(1)
# for spam in range(10):
#     for i in iterator:
#         print(spam*i)

"""test 6 calling using next"""
# iterator = map(lambda x: ord(x), filter(lambda x: ord(x) == 98, "abc"))
# for spam in range(3):
#     while iterator:# this won't work as expected and is really hard to catch!
#         eggs = next(iterator)
#         print("spam ", spam)
#         print("eggs ", eggs)
#         print(chr(spam*eggs))

"""test 7 using list and set"""

iterator1 = list((ord(x) for x in "abc"))
iterator2 = set((ord(x) for x in "aaa"))

for spam in range(3):
    for i1 , i2 in zip(iterator1, iterator2):
        print("i1 ", chr(i1))
        print("i2 ", chr(i2))
        #print(chr(spam + i1), chr(spam + i2))

"""test 8 using same iterator multiple times"""

# sources_iter = (i for i in range(3))
# for output_field in sources_iter:
#     for source in sources_iter:
#         print(output_field, source)

# def get_sources():
#     return (i for i in range(3))
#
# for output_field in get_sources():
#     for source in get_sources(): # Inner loop gets a fresh iterator
#         print(output_field, source)

# from itertools import count
# counter = count(0)
# def get_next(): return next(counter)
# iter_call_obj = iter(get_next, 3)
# for _i in range(2):
#     for item in iter_call_obj: # This is line 6
#         print(item)


#Case 1a: Consumption by list(), tuple(), set(), sorted(), sum(), etc.


# gene = iter(i for i in [1, 2, 3])
# for j in range(10):
#     for k in gene:
#         print("j ", j, "k ", k)
#     for m in gene:
#         print("j ", j, "m ", m)

# custom generator

# def cust_gen(a):
#     for item in a:
#         yield item
#
# gene = cust_gen([1, 2, 3])
# for i in range(10):
#     for k in gene:
#         print("i ", i, "k ", k)

# custom generator returns a new generator instance every time
# def cust_gen(a):
#     yield a+1
#
# gene = (cust_gen(item) for item in [1, 2, 3])
# for i in range(10):
#     for k in gene:
#         print("i ", i, "k ", k)

#
# class TestRepeatedIteratorLoopChecker(CheckerTestCase):
#     """Tests for RepeatedIteratorLoopChecker."""
#
#     CHECKER_CLASS = RepeatedIteratorLoopChecker
#
#     def test_warns_for_generator_expression_global_scope(self):
#         with self.assertAddsMessages(
#             MessageTest(
#                 msg_id="looping-through-iterator",
#                 line=3,
#                 args=("gen_ex",),
#                 confidence=interfaces.HIGH,
#             )
#         ):
#             walked = self.walk( # CHANGED HERE
#                 astroid.parse(
#                     """
#                     gen_ex = (x for x in range(3)) # line 1
#                     for _i in range(2): # line 2
#                         for item in gen_ex: # line 3 <-- Warning here
#                             print(item)
#                     """
#                 )
#             )
#             print("walked ", walked)

"""test9 full exhausted iterators with list, set calls"""
# iterator1 = list((ord(x) for x in "abc"))
# for spam in range(10):
#     for eggs in iterator1:# this won't work as expected and is really hard to catch!
#         # print("spam ", spam)
#         # print("eggs ", eggs)
#         print(spam*eggs)

# false positive
# for i in range(5):
#     iterator1 = (i for i in [1, 2, 3])
#     for j in list(iterator1):
#         print("i ", i, "j ", j)

# """test10 full exhausted iterators with list, set calls after the iterator re initialize"""
# iterator1 = (ord(x) for x in "abc")
#
# for spam in range(10):
#     iterator1 = (i for i in [1,2])
#     for spam1 in range(5):
#         for eggs in iterator1:# this won't work as expected and is really hard to catch!
#             print("spam ", spam)
#             print("eggs ", eggs)
#             print(spam+spam1+eggs)


## false positives
#
# data = [1, 2, 3]
# # 'iter' is in KNOWN_ITERATOR_PRODUCING_FUNCTIONS
# for _i in range(2):
#     my_iter = iter(data)
#     for item in my_iter:
#         print(item)

# iter_empty_map = (i for i in [1,2,3])
# iter_empty_map1 = iter_empty_map
# for i in range(3):
#     for item in iter_empty_map1: # This *will* be exhausted. Checker should flag.
#         print(item)
# for item2 in iter_empty_map:
#     print(item2)


# iter1 = map(lambda x: x, range(5))
# for i in iter1:
#     for j, k in zip(filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))), iter(range(5))):
#         print("i ", i, "j ", j, "k ", k)

# iter1 = map(lambda x:x, range(5))
# for i in filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))):
#     for j, k in zip(iter1, iter(range(5))):
#         print("i ", i, "j ", j, "k ", k)
#
# map_obj = map(str, range(3))
# for _i in range(2):
#     for item in map_obj: # <-- Warning here
#         print(item)



# print("-------------TRUE POSITIVE TEST CASES------------")
# print("------------CREATED USING GENERATOR EXPRESSIONS------------")
# print("------------test1------------ iter1 in nested loop used level 1")
#
# iter1 = (i for i in range(5))
# for i in range(4):
#   for i in iter1:
#     print(i)

# print("------------test2------------ same iter1 in nested loop used level 1")
# iter1 = (i for i in range(5))
# for i in iter1:
#   for j in iter1:
#     print("i ", i, "j ", j)
#
# print("------------test3------------ same iter1 in nested loop used level 2")
# iter1 = (i for i in range(5))
# for i in iter1:
#   for j in range(3):
#     for k in iter1:
#       print("i ", i, "j ", j, "k ", k)

# print("------------test4------------ iter1 in nested loop used level 3")
#
# iter1 = (i for i in range(5))
# for i in range(5):
#   for j in range(3):
#     for k in iter1:
#       print("i ", i, "j ", j, "k ", k)
#
# print(
#     "------------CREATED USING PRODUCING FUNCTIONS LIKE MAP, FILTER, ITER ------------"
# )
# print("------------test1------------ iters in nested loops")
# iter1 = map(lambda x: x, range(5))
# iter2 = filter(lambda x: x % 2 == 0, map(lambda x: x, range(5)))
# iter3 = iter(range(5))
#
# for i in iter1:
#   for j in iter2:
#     for k in iter3:
#       print("i ", i, "j ", j, "k ", k)
# #
# print("------------test2------------ iters in nested loops")
#
# iter1 = map(lambda x: x, range(5))
# iter2 = filter(lambda x: x % 2 == 0, map(lambda x: x, range(5)))
# iter3 = iter(range(5))
#
# for i in iter1:
#   for j, k in zip(iter2, iter3):
#     print("i ", i, "j ", j, "k ", k)
#
# print(
#     "------------test3------------ iters direct use in nested loops without assigning to variable"
# )

# iter1 = map(lambda x: x, range(5))
# for i in range(6):
#   for i in iter1:
#     for j, k in zip(filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))),
#                     iter(range(5))):
#       print("i ", i, "j ", j, "k ", k)
#
# print(
#     "------------test4------------ iters direct use in nested loops level2 without assigning to variable"
# )
# iter1 = map(lambda x: x, range(5))
# for i in filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))):
#     for j, k in zip(iter1, iter(range(5))):
#         print("i ", i, "j ", j, "k ", k)
#
#print("------------NEGATIVE TEST CASES------------ iters in nested loops")

# print(
#     "------------test5------------ iters direct use in nested loops without assigning to variable"
# )
# iter1 = map(lambda x: x, range(5))
# for i in iter1:
#   for j, k in zip(filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))),
#                   iter(range(5))):
#     print("i ", i, "j ", j, "k ", k)

# import string
# iter1 = map(lambda x: x, string.printable)
# iter2 = set(map(lambda x: x, string.printable))
# for i in range(5):
#     for i1, i2 in list(zip(iter1, iter2)):
#         print(i1, i2)
# iterator1 = (i for i in [1, 2, 3])
# for i in range(5):
#     iterator1 = (i for i in [1, 2, 3])
#     for j in list(iterator1):
#         print("i ", i, "j ", j)

# iter1 = map(lambda x: x, range(5))
# for i in filter(lambda x: x % 2 == 0, map(lambda x: x, range(5))):
#     for j, k in zip(iter1, iter(range(5))):
#         print("i ", i, "j ", j, "k ", k)

