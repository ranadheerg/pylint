from typing import Tuple

from pylint.checkers import BaseChecker
from pylint.lint import PyLinter
from astroid import nodes


class RepeatedLoopingIteratorChecker(BaseChecker):

    name = 'repeated_iterator_checker'
    msgs = {
        "W4801": (
            "iterator %s likely exhausted before the loop"
        )
    }
    iter_producing_funcs = {"map", "filter", "zip", "iter", "reversed"}
    itererator_consumers_one_time = {"list", "set", "dict"}

    def __init__(self, linter: PyLinter) -> None:
        super().__init__(linter)
        #key - (id of scope of iterator, )
        #hashmap for lookup across forloops with scope node of assignment defined and iterator name as key
        # and for node or function call , iterator_assignment_node,
        self._iterator_lookup_dict: dict[Tuple[nodes.NodeNG, str], [nodes.NodeNG, nodes.Assign]] = {}

    def visit_module(self, _:nodes.Module):
        self._iterator_lookup_dict.clear()


    def visit_assign(self, assign_node: nodes.Assign):
        # check if generator expression is assigned to a variable
        # Can be a ganerator of format () or a function call like map, filter, zip, iter
        is_one_variable = len(assign_node.targets) == 1 and isinstance(assign_node.targets[0], nodes.AssignName)
        if is_one_variable:
            assign_var_name = assign_node.targets[0]
            assigned_value = assign_node.value
            dict_key = (assign_node.scope(), assign_var_name.name)
            is_gen_exp = isinstance(assigned_value, nodes.GeneratorExp)
            is_func_call = (isinstance(assigned_value, nodes.Call) and
                            isinstance(assigned_value.func, nodes.NodeNG))
            is_gen_exhaust_func_call = is_func_call and assigned_value.func.name in self.iter_producing_funcs
            # bool to define iter() call without any arguments
            is_empty_iter_call = is_func_call and assigned_value.func.name == "iter" and not assigned_value.func.args
            if is_empty_iter_call:
                pass
            if is_gen_exp or is_gen_exhaust_func_call:
                # ignore empty iteration calls
                self._iterator_lookup_dict[
                    dict_key
                ] = (assigned_value, assign_node)

            else:
                # shadowing the previous iterator assignment with non iterator
                if dict_key in self._iterator_lookup_dict:
                    del self._iterator_lookup_dict[dict_key]

    def visit_for(self, for_node: nodes.For):

        pass

    def visit_call(self, func_node: nodes.Call):
        pass
