# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Set

from astroid import nodes

from pylint import checkers, interfaces
from pylint.checkers import utils

if TYPE_CHECKING:
    from pylint.lint import PyLinter


class RepeatedIteratorLoopChecker(checkers.BaseChecker):
    """
    Checks for exhaustible iterators (e.g., generator expressions, results of
    map(), filter(), zip(), iter()) that are defined in an
    outer scope and then looped over or consumed by a function call in a
    nested loop. This pattern often leads to the iterator being exhausted
    after the first full pass, causing unexpected behavior.
    """

    name = "repeated_iterator_loop"
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

    options = ()

    KNOWN_ITERATOR_PRODUCING_FUNCTIONS: Set[str] = {
        "map", "filter", "zip", "iter", "reversed"
    }

    KNOWN_ITERATOR_CONSUMING_FUNCTIONS: Set[str] = {
        "list", "tuple", "set", "sorted", "sum", "min", "max", "all", "any", "dict",
    }

    def __init__(self, linter: PyLinter | None = None) -> None:
        super().__init__(linter)
        self._assigned_iterators: Dict[
            Tuple[nodes.NodeNG, str], Tuple[nodes.NodeNG, nodes.Assign]
        ] = {}

    def visit_module(self, _: nodes.Module) -> None:
        self._assigned_iterators.clear()

    def visit_assign(self, node: nodes.Assign) -> None:
        if len(node.targets) == 1 and isinstance(node.targets[0], nodes.AssignName):
            target_assign_name_node = node.targets[0]
            var_name = target_assign_name_node.name
            scope_of_assignment = target_assign_name_node.scope()
            lookup_key = (scope_of_assignment, var_name)
            value_node = node.value

            is_value_a_tracked_exhaustible_iterator = False
            iterator_producing_node_for_tracking: nodes.NodeNG | None = None

            if isinstance(value_node, nodes.GeneratorExp):
                is_value_a_tracked_exhaustible_iterator = True
                iterator_producing_node_for_tracking = value_node
            elif (
                isinstance(value_node, nodes.Call)
                and isinstance(value_node.func, nodes.Name)
                and value_node.func.name in self.KNOWN_ITERATOR_PRODUCING_FUNCTIONS
            ):
                is_value_a_tracked_exhaustible_iterator = True
                iterator_producing_node_for_tracking = value_node

            if is_value_a_tracked_exhaustible_iterator and iterator_producing_node_for_tracking:
                self._assigned_iterators[lookup_key] = (
                    iterator_producing_node_for_tracking,
                    node, # The Assign node itself
                )
            else:
                if lookup_key in self._assigned_iterators:
                    del self._assigned_iterators[lookup_key]

    def _find_tracked_iterator_assignment_node(
        self, var_name: str, usage_scope: nodes.NodeNG
    ) -> nodes.Assign | None:
        """
        Searches for the Assign node of a tracked exhaustible iterator variable.
        Returns the astroid.nodes.Assign node or None.
        """
        current_search_scope: nodes.NodeNG | None = usage_scope
        while current_search_scope:
            lookup_key = (current_search_scope, var_name)
            if lookup_key in self._assigned_iterators:
                _iterator_producing_node, assignment_node = self._assigned_iterators[lookup_key]
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
            usage_context_node: nodes.NodeNG,
            # True if the usage is direct iteration (from visit_for),
            # False if usage is a call consuming the iterator (from visit_call).
            is_usage_direct_iteration: bool
    ) -> bool:
        """
        Checks if the given iterator is defined outside an ancestor loop
        of usage_context_node where it's used/consumed. Adds a message if so.
        Returns True if a message was added, False otherwise.
        """
        # Start searching for an ancestor loop from the parent of the usage context.
        # For visit_for, usage_context_node is the For loop itself (L_inner), so parent is L_outer.
        # For visit_call, usage_context_node is the Call node (C1), so parent could be the For loop (L_j) for which C1 is the iterable.
        parent_walker = usage_context_node.parent

        while parent_walker:
            if isinstance(parent_walker, nodes.For):  # Found an ancestor loop
                ancestor_loop_node = parent_walker

                if not is_usage_direct_iteration:  # Called from visit_call
                    # If the Call node (usage_context_node) is the .iter attribute of this ancestor_loop_node,
                    # it means this loop (ancestor_loop_node) iterates over the *result* of the call.
                    # This loop itself does not cause re-evaluation of the call with the same iterator.
                    # We must look for a loop that is an ancestor of *this* ancestor_loop_node.
                    if hasattr(ancestor_loop_node, "iter") and usage_context_node is ancestor_loop_node.iter:
                        # Continue to the next parent, this loop isn't the one causing re-consumption by the call.
                        if not hasattr(parent_walker, 'parent') or parent_walker.parent is parent_walker:
                            break
                        parent_walker = parent_walker.parent
                        continue

                # At this point, ancestor_loop_node is a loop that would re-execute
                # the direct iteration (if is_usage_direct_iteration is True)
                # or re-execute the call node (if is_usage_direct_iteration is False and the above 'continue' was not hit).
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

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_for(self, current_for_node: nodes.For) -> None:
        iterated_expression_node = current_for_node.iter

        if not isinstance(iterated_expression_node, nodes.Name):
            return

        iterator_variable_name = iterated_expression_node.name
        assignment_node_of_iterator = \
            self._find_tracked_iterator_assignment_node(iterator_variable_name, iterated_expression_node.scope())

        if not assignment_node_of_iterator:
            return

        self._check_iterator_misuse_in_ancestor_loop(
            iterator_name_node=iterated_expression_node,
            iterator_variable_name=iterator_variable_name,
            assignment_node_of_iterator=assignment_node_of_iterator,
            usage_context_node=current_for_node,
            is_usage_direct_iteration=True
        )

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_call(self, call_node: nodes.Call) -> None:
        if not isinstance(call_node.func, nodes.Name):
            return

        called_func_name = call_node.func.name
        if called_func_name not in self.KNOWN_ITERATOR_CONSUMING_FUNCTIONS:
            return

        for arg_node in call_node.args:
            if not isinstance(arg_node, nodes.Name):
                continue

            iterator_variable_name = arg_node.name
            assignment_node_of_iterator = \
                self._find_tracked_iterator_assignment_node(iterator_variable_name, arg_node.scope())

            if not assignment_node_of_iterator:
                continue

            if self._check_iterator_misuse_in_ancestor_loop(
                iterator_name_node=arg_node,
                iterator_variable_name=iterator_variable_name,
                assignment_node_of_iterator=assignment_node_of_iterator,
                usage_context_node=call_node,
                is_usage_direct_iteration=False
            ):
                return # Message added for this argument, stop processing this call_node

    def _is_node_equal_or_descendant_of(
        self, node: nodes.NodeNG, ancestor: nodes.NodeNG
    ) -> bool:
        current: nodes.NodeNG | None = node
        while current:
            if current == ancestor:
                return True
            if not hasattr(current, 'parent') or current.parent is current:
                break
            current = current.parent
        return False

def register(linter: PyLinter) -> None:
    linter.register_checker(RepeatedIteratorLoopChecker(linter))