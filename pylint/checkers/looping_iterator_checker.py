# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import logging  # Added for debugging
from typing import TYPE_CHECKING, Set, Dict

from astroid import Uninferable, nodes
from astroid.exceptions import InferenceError

from pylint import checkers, interfaces
from pylint.checkers import utils

if TYPE_CHECKING:
    from pylint.lint import PyLinter


class RepeatedIteratorLoopChecker(checkers.BaseChecker):
    """
    Checks for exhaustible iterators that are re-used in a nested loop.
    """

    name = "looping-through-iterator"
    msgs = {
        "W4801": (
            "Iterator '%s' from an outer scope is re-used or consumed in a nested loop.",
            "looping-through-iterator",
            "...",
        )
    }

    options = ()

    # A set of built-in functions that are known to produce single-use iterators.
    KNOWN_ITERATOR_PRODUCING_FUNCTIONS: Set[str] = {
        "map", "filter", "zip", "iter", "reversed"
    }
    # A set of functions that consume iterators. `zip` is in both lists.
    KNOWN_ITERATOR_CONSUMING_FUNCTIONS: Set[str] = {
        "list", "tuple", "set", "sorted", "sum", "min", "max", "all", "any", "dict", "zip",
    }

    def __init__(self, linter: PyLinter | None = None) -> None:
        super().__init__(linter)
        # This is the stateful cache. It maps an iterator's variable name
        # to the AST node where it was created.
        # e.g., {"my_iter": <Call node for iter(...)>}
        self.iterator_origins: Dict[str, nodes.NodeNG] = {}

    # --- Stateful Part: Proactively Caching Definitions ---

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_assign(self, node: nodes.Assign) -> None:
        """
        This method is part of the stateful approach. It's called for any
        assignment, like `x = ...`, and its job is to find and cache any
        assignments that create a known iterator.
        """
        value = node.value  # The right-hand side of the '='

        # Check if the right-hand side is a generator or a call to a function
        # that we know produces an iterator.
        is_iterator_definition = False
        if isinstance(value, nodes.GeneratorExp):
            is_iterator_definition = True
        elif (isinstance(value, nodes.Call)
              and isinstance(value.func, nodes.Name)
              and value.func.name in self.KNOWN_ITERATOR_PRODUCING_FUNCTIONS):
            is_iterator_definition = True

        if not is_iterator_definition:
            return

        # We found an iterator definition. Now, get the variable name(s)
        # from the left-hand side and cache the definition.
        for target in node.targets:
            if isinstance(target, nodes.AssignName):
                iterator_name = target.name
                print(f"DEBUG (Assign): Caching definition for '{iterator_name}'")
                self.iterator_origins[iterator_name] = value

    # --- Reactive Part: Triggering Checks on Usage ---

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_for(self, node: nodes.For) -> None:
        """This method is a reactive trigger. It's called for every `for` loop."""
        if isinstance(node.iter, nodes.Name):
            # The loop is `for ... in my_variable:`. We need to check `my_variable`.
            self._check_iterator_usage(node.iter, usage_context_node=node)

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_call(self, node: nodes.Call) -> None:
        """This method is a reactive trigger. It's called for every function call."""
        # Check if the function is one that consumes iterators (e.g., list(), sum()).
        if (isinstance(node.func, nodes.Name)
                and node.func.name in self.KNOWN_ITERATOR_CONSUMING_FUNCTIONS):
            # Check each argument passed to the function.
            for arg in node.args:
                if isinstance(arg, nodes.Name):
                    self._check_iterator_usage(arg, usage_context_node=node)

    # --- Core Hybrid Logic ---

    def _check_iterator_usage(
            self,
            iterator_name_node: nodes.Name,
            usage_context_node: nodes.NodeNG
    ) -> None:
        """
        This is the core of the hybrid checker. It now uses a more robust
        method to identify nested loops and check the definition scope.
        """
        iterator_name = iterator_name_node.name
        print(f"DEBUG (Usage): --- Checking usage of '{iterator_name}' at line {iterator_name_node.lineno} ---")

        # 1. Find the loop that directly contains the usage.
        usage_loop = self._find_ancestor_loop(usage_context_node)
        if not usage_loop:
            # The usage is not inside any loop, so it can't be a nested re-use.
            return

        # 2. Find the loop that contains the usage_loop (the "outer" loop).
        outer_loop = self._find_ancestor_loop(usage_loop.parent)
        if not outer_loop:
            # The usage is in a top-level loop, not a nested one.
            # We only want to check for re-use in nested loops.
            # (You could expand this to check for module-level iterators later).
            print(f"DEBUG (Usage): Usage of '{iterator_name}' is in a top-level loop. Skipping.")
            return

        print(f"DEBUG (Usage): Nested loop detected. Inner at L{usage_loop.lineno}, Outer at L{outer_loop.lineno}")

        # 3. Get the definition node from our cache.
        definition_node = self.iterator_origins.get(iterator_name)
        if not definition_node:
            # For now, we only handle cases where we reliably cached the definition.
            # The fallback to inference can be added back later if needed.
            return

        # 4. Check the position of the definition. The definition is valid if it
        #    occurs inside the outer loop, as it gets re-initialized.
        #    The violation occurs if the definition is OUTSIDE the outer loop.
        position_check_node = definition_node.parent  # The 'Assign' node
        is_defined_inside_outer_loop = self._is_node_descendant_of(position_check_node, outer_loop)

        print(f"DEBUG (Position): Is '{iterator_name}' defined inside the outer loop? {is_defined_inside_outer_loop}")

        if not is_defined_inside_outer_loop:
            print(f"DEBUG (Position): >>> VIOLATION FOUND! Firing message for '{iterator_name}'! <<<")
            self.add_message(
                "looping-through-iterator",
                node=iterator_name_node,
                args=(iterator_name,),
                confidence=interfaces.HIGH,
            )

    # --- Helper Methods ---

    def _check_definition_position(
            self,
            definition_node: nodes.NodeNG,
            ancestor_loop_node: nodes.NodeNG,
            usage_node: nodes.Name
    ) -> None:
        """
        Given a definition and a loop, checks if the definition is outside
        the loop. If it is, a Pylint message is fired.
        """
        # The `definition_node` we have is the right-hand side of an assignment
        # (e.g., the GeneratorExp). To check its position, we must look at its
        # parent, which is the `Assign` node itself.
        position_check_node = definition_node.parent

        is_defined_inside_loop = self._is_node_descendant_of(position_check_node, ancestor_loop_node)
        print(f"DEBUG (Position): Is '{usage_node.name}' defined inside the loop? {is_defined_inside_loop}")

        if not is_defined_inside_loop:
            print(f"DEBUG (Position): >>> VIOLATION FOUND! Firing message for '{usage_node.name}'! <<<")
            self.add_message(
                "looping-through-iterator",
                node=usage_node,
                args=(usage_node.name,),
                confidence=interfaces.HIGH,
            )

    def _find_ancestor_loop(self, node: nodes.NodeNG) -> nodes.For | nodes.While | None:
        """Walks up the AST from a node to find the first containing loop."""
        current: nodes.NodeNG | None = node
        while current:
            # If we find a loop, return it.
            if isinstance(current, (nodes.For, nodes.While)):
                return current
            # Don't walk past the boundary of a function or class.
            if isinstance(current, (nodes.FunctionDef, nodes.ClassDef, nodes.Module)):
                return None
            current = current.parent
        return None

    def _is_node_descendant_of(self, node: nodes.NodeNG, ancestor: nodes.NodeNG) -> bool:
        """Checks if `node` is a descendant of or is the same as `ancestor`."""
        current: nodes.NodeNG | None = node
        while current:
            if current == ancestor:
                return True
            # Stop searching if we go past a function/class boundary.
            if isinstance(current, (nodes.FunctionDef, nodes.ClassDef, nodes.Module)):
                break
            current = current.parent
        return False


def register(linter: PyLinter) -> None:
    """This required function is called by Pylint to register the checker."""
    linter.register_checker(RepeatedIteratorLoopChecker(linter))
