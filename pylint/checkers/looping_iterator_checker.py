from typing import Tuple

from pylint import interfaces
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter
from astroid import nodes


class RepeatedLoopingIteratorChecker(BaseChecker):

    name = 'repeated_iterator_checker'
    msgs = {
        "W4801": (
            "Iterator '%s' (defined as a generator expression or by a call to a "
            "known iterator-producing function like map(), filter(), zip(), iter() "
            "in an outer scope) is re-used or consumed in a nested loop. "
            "It will likely be exhausted after the first full pass, "
            "leading to unexpected behavior in subsequent iterations of the outer loop.",
            "looping-through-iterator",
            "Emitted when an exhaustible iterator (e.g., generator expression, map/filter object) "
            "defined in an outer scope is iterated over or consumed by a function "
            "(e.g. list(), sum()) multiple times within a nested loop. "
            "This typically means the iterator will be empty for subsequent iterations. "
            "Consider re-initializing the iterator inside the outer loop if fresh iteration "
            "or consumption is needed, or convert it to a list (once, outside the "
            "re-consuming loop) if it must be reused and fits in memory.",
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
        print("DEBUG: inside _get_iterator_assign_node")
        current_search_scope: nodes.NodeNG | None = usage_scope
        print("DEBUG: printing current search scope")
        print(current_search_scope)
        while current_search_scope:
            lookup_key = (current_search_scope, var_name)
            print("DEBUG: printing lookup_key ")
            print(lookup_key)
            if lookup_key in self._iterator_lookup_dict:
                _iterator_producing_node, assignment_node = self._iterator_lookup_dict[lookup_key]
                print("DEBUG: returning assignment node")
                print(assignment_node)
                return assignment_node
            if not hasattr(current_search_scope, 'parent_scope') or \
                    current_search_scope.parent_scope is current_search_scope:
                print("breaking out of _get_iterator_assign_node")
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
        print("DEBUG: Inside _check_iterator_misuse_in_ancestor_loop method")
        parent_walker = usage_context_node.parent
        while parent_walker:
            print("DEBUG: Inside while loop ")
            print("printing parent walker")
            print(parent_walker)
            if isinstance(parent_walker, nodes.For):  # This is the ancestor loop
                print("DEBUG: parent walker is for node")
                ancestor_loop_node = parent_walker
                print("DEBUG: calling method _is_node_equal_or_descendant_of with below arguments")
                print("DEBUG: assignment_node_of_iterator ")
                print(assignment_node_of_iterator)
                print("DEBUG: ancestor_loop_node")
                print(ancestor_loop_node)
                if not self._is_node_equal_or_descendant_of(
                        assignment_node_of_iterator, ancestor_loop_node
                ):
                    print("DEBUG: adding message since _is_node_equal_or_descendant_of returned False")
                    self.add_message(
                        "looping-through-iterator",
                        node=iterator_name_node,
                        args=(iterator_variable_name,),
                        confidence=interfaces.HIGH,
                    )
                    return True  # Message added
            if not hasattr(parent_walker, 'parent') or parent_walker.parent is parent_walker:
                print("DEBUG: breaking out of while loop inside _check_iterator_misuse_in_ancestor_loop")
                break
            parent_walker = parent_walker.parent
        return False  # No message added


    def visit_assign(self, assign_node: nodes.Assign):
        # check if generator expression is assigned to a variable
        # Can be a ganerator of format () or a function call like map, filter, zip, iter
        is_one_variable = len(assign_node.targets) == 1 and isinstance(assign_node.targets[0], nodes.AssignName)
        print("DEBUG: inside visit_assign is_one_variable ", is_one_variable)
        if is_one_variable:
            assign_var_name = assign_node.targets[0]
            print("DEBUG: assign variable name ", assign_var_name)
            assigned_value = assign_node.value
            print("DEBUG: printing assigned value")
            print(assigned_value)
            dict_key = (assign_node.scope(), assign_var_name.name)
            print("DEBUG: printing dict key (scope, variable name)")
            is_gen_exp = isinstance(assigned_value, nodes.GeneratorExp)
            print("DEBUG: is_gen_exp ", is_gen_exp)
            is_func_call = (isinstance(assigned_value, nodes.Call) and
                            isinstance(assigned_value.func, nodes.NodeNG))
            print("DEBUG: is_func_call ", is_func_call)
            is_gen_exhaust_func_call = is_func_call and assigned_value.func.name in self.iter_producing_funcs
            print("DEBUG: is_gen_exhaust_funct_call ", is_gen_exhaust_func_call)
            # bool to define iter() call without any arguments
            is_empty_iter_call = is_func_call and assigned_value.func.name == "iter" and not assigned_value.func.args
            print("DEBUG: is_empty_iter_call ", is_empty_iter_call)
            if is_empty_iter_call:
                print("DEBUG: empty iter() call detected")
                pass
            if is_gen_exp or is_gen_exhaust_func_call:
                print("DEBUG: gen exp or gen producing func call detected")
                self._iterator_lookup_dict[
                    dict_key
                ] = (assigned_value, assign_node)
                print("DEBUG: updated state of lookup dict ")
                print("DEBUG: updating dict key ", dict_key)
                print("DEBUG: with dict value ", (assigned_value, assign_node))

            else:
                # shadowing the previous iterator assignment with non iterator
                print("DEBUG: inside else in visit_assign ")
                if dict_key in self._iterator_lookup_dict:
                    print("DEBUG: dict_key already present in lookup dict so removing it")
                    del self._iterator_lookup_dict[dict_key]
                print("DEBUG: out of else in visit_assign")
        print("------------ out of visit_assign --------------")

    def visit_for(self, for_node: nodes.For):

        for_exp_node = for_node.iter
        print("DEBUG: -----------Inside visit_for ----------------")
        if isinstance(for_exp_node, nodes.Name):
            print("DEBUG: detected named exp node")
            #variable name
            iterator_name = for_exp_node.name
            print("DEBUG: iterator_name ", iterator_name)
            assignment_node = self._get_iterator_assign_node(iterator_name, for_exp_node.scope())
            print("DEBUG: printing assignment_node found")
            print(assignment_node)
            if assignment_node:
                print("DEBUG: checking for misuse in ancestor loop")
                self._check_iterator_misuse_in_ancestor_loop(
                    iterator_name_node=for_exp_node,
                    iterator_variable_name=iterator_name,
                    assignment_node_of_iterator=assignment_node,
                    usage_context_node=for_node
                )
        print("DEBUG: ------------ out of visit for -------------")


    def visit_call(self, call_node: nodes.Call):

        print("DEBUG: ----------------- Inside visit_call -------------------")
        if isinstance(call_node.func, nodes.Name):
            print("DEBUG: Detected named function")
            func_name = call_node.func.name
            print("DEBUG: func_name ", func_name)
            if func_name in self.itererator_consumers_one_time:
                print("DEBUG: function is in consumer list")
                print("DEBUG: printing function args")
                print(call_node.args)
                for arg_node in call_node.args:
                    print("DEBUG: visiting arg_node ")
                    if isinstance(arg_node, nodes.Name):
                        print("DEBUG: arg_node is named node")
                        iterator_name = arg_node.name
                        print("DEBUG: arg_node name => iterator_name ", arg_node.name)
                        assignment_node = self._get_iterator_assign_node(iterator_name, arg_node.scope())
                        print("DEBUG: assignment_node looked up ")
                        if assignment_node:
                            print("DEBUG: assignment_node found ")
                            print("DEBUG: calling iterator misuse in ancestor loop")
                            if self._check_iterator_misuse_in_ancestor_loop(
                                    iterator_name_node=arg_node,
                                    iterator_variable_name=iterator_name,
                                    assignment_node_of_iterator=assignment_node,
                                    usage_context_node=call_node
                            ):
                                print("DEBUG: _check_iterator_misuse_in_ancestor_loop call completed")
                                return  # Message added for this argument, stop processing this call_node
                        else:
                            print("DEBUG: assignment node not found moving to next arg")
                            continue
                    else:
                        print("DEBUG: arg_node is not named moving to next arg")
                        continue
        print("DEBUG: ------------ out of visit call -------------")

    def _is_node_equal_or_descendant_of(self, node: nodes.NodeNG, ancestor: nodes.NodeNG) -> bool:
        current: nodes.NodeNG | None = node
        print("DEBUG: Inside method _is_node_equal_or_descendant_of")
        while current:
            print("DEBUG: Inside _is_node_equal_or_descendant_of while loop")
            print("printing current node ")
            print(current)
            print("printing ancestor node ")
            print(ancestor)
            if current == ancestor:
                print("current = ancestor --- so returning true")
                return True
            if not hasattr(current, 'parent') or current.parent is current:
                print("DEBUG: Breaking out of while loop inside _is_node_equal_or_descendant_of")
                break
            current = current.parent
        return False


def register(linter: PyLinter) -> None:
    linter.register_checker(RepeatedLoopingIteratorChecker(linter))
