# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Set, List

from astroid import nodes

from pylint import checkers, interfaces
from pylint.checkers import utils

if TYPE_CHECKING:
    from pylint.lint import PyLinter


class RepeatedIteratorLoopChecker(checkers.BaseChecker):
    """
    Checks for exhaustible iterators that are looped over in a nested loop.
    """

    name = "repeated_iterator_loop"
    msgs = {
        "W4801": (
            "Iterator '%s' (defined in an outer scope) is re-used in a nested loop. "
            "It will likely be exhausted after the first iteration of the outer loop.",
            "looping-through-iterator",
            "...",  # Your detailed help message
        )
    }

    options = ()

    KNOWN_ITERATOR_PRODUCING_FUNCTIONS: Set[str] = {
        "map", "filter", "zip", "iter", "reversed"
    }

    KNOWN_ITERATOR_CONSUMING_FUNCTIONS: Set[str] = {
        "list", "tuple", "set", "sorted", "sum", "min", "max", "all", "any", "dict", "zip",
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
            target_name_node = node.targets[0]
            var_name = target_name_node.name
            scope = target_name_node.scope()
            lookup_key = (scope, var_name)
            value_node = node.value

            is_iterator = False
            if isinstance(value_node, nodes.GeneratorExp):
                is_iterator = True
            elif (
                    isinstance(value_node, nodes.Call)
                    and isinstance(value_node.func, nodes.Name)
                    and value_node.func.name in self.KNOWN_ITERATOR_PRODUCING_FUNCTIONS
            ):
                is_iterator = True

            if is_iterator:
                self._assigned_iterators[lookup_key] = (value_node, node)
            elif lookup_key in self._assigned_iterators:
                del self._assigned_iterators[lookup_key]

    def _find_tracked_iterator_assignment_node(
            self, var_name: str, usage_scope: nodes.NodeNG
    ) -> nodes.Assign | None:
        scope = usage_scope
        while scope:
            if (scope, var_name) in self._assigned_iterators:
                _, assignment_node = self._assigned_iterators[(scope, var_name)]
                return assignment_node
            if not hasattr(scope, 'parent') or scope.parent is scope:
                break
            scope = scope.parent
        return None

    def _is_descendant_of_for_iterable(self, node: nodes.NodeNG) -> bool:
        """Check if a node is a descendant of a For loop's `iter` attribute."""
        current = node
        # Stop if we hit the direct parent For loop, as we only care if we're in its `.iter` part
        while hasattr(current, "parent") and not isinstance(current, nodes.For):
            parent = current.parent
            if isinstance(parent, nodes.For) and parent.iter == current:
                return True
            current = parent
        return False

    def _check_iterator_misuse_in_ancestor_loop(
            self, iterator_name_node: nodes.Name, usage_context_node: nodes.NodeNG
    ) -> None:
        iterator_variable_name = iterator_name_node.name
        assignment_node = self._find_tracked_iterator_assignment_node(
            iterator_variable_name, iterator_name_node.scope()
        )
        if not assignment_node:
            return

        parent = usage_context_node.parent
        while parent:
            if isinstance(parent, (nodes.For, nodes.While, nodes.Comprehension)):
                ancestor_loop = parent
                if not self._is_node_equal_or_descendant_of(assignment_node, ancestor_loop):
                    self.add_message(
                        "looping-through-iterator",
                        node=iterator_name_node,
                        args=(iterator_variable_name,),
                        confidence=interfaces.HIGH,
                    )
                    return  # Add message once and stop
            if not hasattr(parent, 'parent') or parent.parent is parent:
                break
            parent = parent.parent

    def _get_iterator_name_nodes(self, expr: nodes.NodeNG) -> list[nodes.Name]:
        if isinstance(expr, nodes.Name):
            return [expr]
        if (
                isinstance(expr, nodes.Call)
                and isinstance(expr.func, nodes.Name)
                and expr.func.name in self.KNOWN_ITERATOR_CONSUMING_FUNCTIONS
        ):
            names = []
            for arg in expr.args:
                names.extend(self._get_iterator_name_nodes(arg))
            return names
        return []

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_for(self, node: nodes.For) -> None:
        """This method handles all misuse within a loop's iterable expression."""
        for name_node in self._get_iterator_name_nodes(node.iter):
            self._check_iterator_misuse_in_ancestor_loop(name_node, node)

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_call(self, node: nodes.Call) -> None:
        """This method handles misuse in other calls, skipping those in loop iterables."""
        # **THE FIX IS HERE**
        # If this call is part of a for-loop's iterable, skip it.
        # visit_for is already handling it, and this prevents duplicate messages.
        if self._is_descendant_of_for_iterable(node):
            return

        if (
                isinstance(node.func, nodes.Name)
                and node.func.name in self.KNOWN_ITERATOR_CONSUMING_FUNCTIONS
        ):
            for name_node in self._get_iterator_name_nodes(node):
                self._check_iterator_misuse_in_ancestor_loop(name_node, node)

    def _is_node_equal_or_descendant_of(
            self, node: nodes.NodeNG, ancestor: nodes.NodeNG
    ) -> bool:
        current = node
        while current:
            if current == ancestor:
                return True
            if not hasattr(current, 'parent') or current.parent is current:
                break
            current = current.parent
        return False


def register(linter: PyLinter) -> None:
    linter.register_checker(RepeatedIteratorLoopChecker(linter))