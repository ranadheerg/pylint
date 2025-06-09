# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from astroid import nodes

from pylint import checkers, interfaces
from pylint.checkers import utils

if TYPE_CHECKING:
    from pylint.lint import PyLinter


class RepeatedIteratorLoopChecker(checkers.BaseChecker):
    """
    Checks for exhaustible iterators that are looped over or consumed
    repeatedly in a loop.
    """

    # FIX 1: The checker's 'name' is now distinct from the message symbol.
    name = "reused-iterator-checker"
    msgs = {
        "W4802": (
            "Iterator '%s' is re-used in a loop. It will likely be exhausted after the first iteration.",
            "reused-iterator",  # This is the message symbol.
            "Emitted when an exhaustible iterator (e.g., a generator, or the result of map(), "
            "filter(), zip()) is defined outside of a loop and is used in a way that "
            "would consume it on each iteration. This leads to unexpected empty results on "
            "all but the first pass. To fix this, either convert the iterator to a list "
            "before the loop if it needs to be reused, or re-create the iterator inside "
            "the loop if a fresh one is needed each time.",
        )
    }

    options = ()

    KNOWN_ITERATOR_PRODUCERS: Set[str] = {"map", "filter", "zip", "iter", "reversed"}
    KNOWN_ITERATOR_CONSUMERS: Set[str] = {
        "list", "tuple", "set", "sorted", "sum", "min", "max", "all", "any", "dict", "zip",
    }

    def __init__(self, linter: PyLinter | None = None) -> None:
        super().__init__(linter)
        self._tracked_iterators: Dict[Tuple[nodes.NodeNG, str], nodes.Assign] = {}
        self._flagged_in_loop_stack: List[Set[str]] = []

    def visit_module(self, _: nodes.Module) -> None:
        self._tracked_iterators.clear()
        self._flagged_in_loop_stack.clear()

    @utils.only_required_for_messages("reused-iterator")
    def visit_assign(self, node: nodes.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0], nodes.AssignName):
            return

        target = node.targets[0]
        key = (target.scope(), target.name)
        value = node.value

        is_iterator = isinstance(value, nodes.GeneratorExp) or (
                isinstance(value, nodes.Call)
                and isinstance(value.func, nodes.Name)
                and value.func.name in self.KNOWN_ITERATOR_PRODUCERS
        )

        if is_iterator:
            self._tracked_iterators[key] = node
        elif key in self._tracked_iterators:
            del self._tracked_iterators[key]

    def _push_loop_scope(self, _: nodes.NodeNG) -> None:
        self._flagged_in_loop_stack.append(set())

    def _pop_loop_scope(self, _: nodes.NodeNG) -> None:
        self._flagged_in_loop_stack.pop()

    # Aliases for loop types that only need to manage the stack
    visit_while = visit_listcomp = visit_setcomp = visit_dictcomp = visit_generatorexp = _push_loop_scope
    leave_for = leave_while = leave_listcomp = leave_setcomp = leave_dictcomp = leave_generatorexp = _pop_loop_scope

    def _find_iterator_assignment(self, name_node: nodes.Name) -> nodes.Assign | None:
        scope = name_node.scope()
        while scope:
            key = (scope, name_node.name)
            if key in self._tracked_iterators:
                return self._tracked_iterators[key]
            if not hasattr(scope, "parent") or scope is scope.parent:
                break
            scope = scope.parent
        return None

    @staticmethod
    def _get_containing_loop(node: nodes.NodeNG) -> Optional[nodes.NodeNG]:
        current = node.parent
        while current:
            if isinstance(current,
                          (nodes.For, nodes.While, nodes.ListComp, nodes.SetComp, nodes.DictComp, nodes.GeneratorExp)):
                return current
            if isinstance(current, (nodes.Module, nodes.FunctionDef, nodes.ClassDef)):
                return None
            current = current.parent
        return None

    def _check_iterator_usage(self, name_node: nodes.Name) -> None:
        if not self._flagged_in_loop_stack:
            return

        var_name = name_node.name
        flagged_set = self._flagged_in_loop_stack[-1]

        if var_name in flagged_set:
            return

        assignment_node = self._find_iterator_assignment(name_node)
        if not assignment_node:
            return

        containing_loop = self._get_containing_loop(name_node)
        if not containing_loop:
            return

        current = assignment_node
        is_defined_inside = False
        while current:
            if current == containing_loop:
                is_defined_inside = True
                break
            current = current.parent

        if not is_defined_inside:
            self.add_message("reused-iterator", node=name_node, args=(var_name,))
            flagged_set.add(var_name)

    @utils.only_required_for_messages("reused-iterator")
    def visit_for(self, node: nodes.For) -> None:
        """Checks for direct iteration over a tracked iterator."""
        # FIX 2: Explicitly call _push_loop_scope here.
        self._push_loop_scope(node)
        if isinstance(node.iter, nodes.Name):
            self._check_iterator_usage(node.iter)

    @utils.only_required_for_messages("reused-iterator")
    def visit_call(self, node: nodes.Call) -> None:
        """Checks for consumption of a tracked iterator by a function call."""
        if not (isinstance(node.func, nodes.Name) and node.func.name in self.KNOWN_ITERATOR_CONSUMERS):
            return

        for arg in node.args:
            if isinstance(arg, nodes.Name):
                self._check_iterator_usage(arg)


def register(linter: PyLinter) -> None:
    linter.register_checker(RepeatedIteratorLoopChecker(linter))