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

    def _get_iterator_assign_node(
            self, var_name: str, usage_scope: nodes.NodeNG
    ) -> nodes.Assign | None:
        """
        Searches for the Assign node of a tracked exhaustible iterator variable.
        Returns the astroid.nodes.Assign node or None.
        """
        current_search_scope: nodes.NodeNG | None = usage_scope
        while current_search_scope:
            lookup_key = (current_search_scope, var_name)
            if lookup_key in self._iterator_lookup_dict:
                _iterator_producing_node, assignment_node = self._iterator_lookup_dict[lookup_key]
                return assignment_node
            if not hasattr(current_search_scope, 'parent_scope') or \
                    current_search_scope.parent_scope is current_search_scope:
                break
            current_search_scope = current_search_scope.parent_scope
        return None

    def _check_iterator_misuse_in_ancestor_loop(
            self,
            iterator_name_node: nodes.Name,
            iterator_variable_name: str,
            assignment_node_of_iterator: nodes.Assign,
            usage_context_node: nodes.NodeNG
    ) -> bool:
        """
        Checks if the given iterator is defined outside an ancestor loop
        of usage_context_node where it's used/consumed. Adds a message if so.
        Returns True if a message was added, False otherwise.
        """
        parent_walker = usage_context_node.parent
        while parent_walker:
            if isinstance(parent_walker, nodes.For):  # This is the ancestor loop
                ancestor_loop_node = parent_walker
                if not self._is_node_equal_or_descendant_of(
                        assignment_node_of_iterator, ancestor_loop_node
                ):
                    self.add_message(
                        "looping-through-iterator",
                        node=iterator_name_node,
                        args=(iterator_variable_name,),
                        confidence=interfaces.HIGH,
                    )
                    return True  # Message added
            if not hasattr(parent_walker, 'parent') or parent_walker.parent is parent_walker:
                break
            parent_walker = parent_walker.parent
        return False  # No message added


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

        for_exp_node = for_node.iter
        if isinstance(for_exp_node, nodes.Name):
            #variable name
            iterator_name = for_exp_node.name
            assignment_node = self._get_iterator_assign_node(iterator_name, for_exp_node.scope())
            if assignment_node:
                self._check_iterator_misuse_in_ancestor_loop(
                    iterator_name_node=for_exp_node,
                    iterator_variable_name=iterator_name,
                    assignment_node_of_iterator=assignment_node,
                    usage_context_node=for_node
                )

    def visit_call(self, call_node: nodes.Call):

        if isinstance(call_node.func, nodes.Name):
            func_name = call_node.func.name
            if func_name in self.itererator_consumers_one_time:
                for arg_node in call_node.args:
                    if isinstance(arg_node, nodes.Name):
                        iterator_name = arg_node.name
                        assignment_node = self._get_iterator_assign_node(iterator_name, arg_node.scope())
                        if assignment_node:
                            if self._check_iterator_misuse_in_ancestor_loop(
                                    iterator_name_node=arg_node,
                                    iterator_variable_name=iterator_name,
                                    assignment_node_of_iterator=assignment_node,
                                    usage_context_node=call_node
                            ):
                                return  # Message added for this argument, stop processing this call_node
                        else:
                            continue
                    else:
                        continue

    def _is_node_equal_or_descendant_of(self, node: nodes.NodeNG, ancestor: nodes.NodeNG) -> bool:
        current: nodes.NodeNG | None = node
        while current:
            if current == ancestor:
                return True
            if not hasattr(current, 'parent') or current.parent is current:
                break
            current = current.parent
        return False


def register(linter: PyLinter) -> None:
    linter.register_checker(RepeatedLoopingIteratorChecker(linter))
