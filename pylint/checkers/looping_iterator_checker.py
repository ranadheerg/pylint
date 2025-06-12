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

    KNOWN_ITERATOR_QUALIFIED_NAMES: Set[str] = {
        "builtins.map", "builtins.filter", "builtins.zip", "builtins.iter", "builtins.reversed"
    }

    # --- Reactive Triggers ---

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_for(self, node: nodes.For) -> None:
        """This method is a reactive trigger. It's called for every `for` loop."""
        if isinstance(node.iter, nodes.Name):
            # The loop is `for ... in my_variable:`. We need to check `my_variable`.
            self._check_iterator_usage(node.iter)

    # --- Core Logic ---

    def _check_iterator_usage(self, iterator_name_node: nodes.Name) -> None:
        """
        This is the core of the checker. It uses inference to determine the
        true nature and scope of the variable at the point of usage.
        """
        iterator_name = iterator_name_node.name
        print(f"DEBUG (Usage): --- Checking usage of '{iterator_name}' at line {iterator_name_node.lineno} ---")

        # 1. Find the loop directly containing the usage.
        usage_loop = self._find_ancestor_loop(iterator_name_node)
        if not usage_loop:
            return

        # 2. Find the loop that contains the usage_loop (the "outer" loop).
        outer_loop = self._find_ancestor_loop(usage_loop.parent)
        if not outer_loop:
            return  # This isn't a nested loop scenario we are checking.

        print(f"DEBUG (Usage): Nested loop detected. Inner at L{usage_loop.lineno}, Outer at L{outer_loop.lineno}")

        # 3. Use INFERENCE to find the true definition of the variable at this exact spot.
        #    This correctly handles shadowing and aliasing.
        try:
            inferred_values = list(iterator_name_node.infer())
            if not inferred_values or inferred_values[0] is Uninferable:
                print("DEBUG (Check): Inference failed. Cannot determine variable type.")
                return

            definition_node = inferred_values[0]
            print(f"DEBUG (Check): Inferred definition is: {definition_node}")

            # 4. Check if the inferred definition is an exhaustible iterator we care about.
            is_exhaustible_iterator = False
            if isinstance(definition_node, nodes.GeneratorExp):
                is_exhaustible_iterator = True
            elif hasattr(definition_node, "qname"):  # Check for map, filter, etc.
                if definition_node.qname() in self.KNOWN_ITERATOR_QUALIFIED_NAMES:
                    is_exhaustible_iterator = True

            if not is_exhaustible_iterator:
                print(f"DEBUG (Check): Inferred type is not an exhaustible iterator. Check passed.")
                return

            # 5. The variable is an iterator. Check if it was defined outside the outer loop.
            is_defined_inside_outer_loop = self._is_node_descendant_of(definition_node, outer_loop)
            print(
                f"DEBUG (Position): Is '{iterator_name}' defined inside the outer loop? {is_defined_inside_outer_loop}")

            if not is_defined_inside_outer_loop:
                print(f"DEBUG (Position): >>> VIOLATION FOUND! Firing message for '{iterator_name}'! <<<")
                self.add_message(
                    "looping-through-iterator",
                    node=iterator_name_node,
                    args=(iterator_name,),
                    confidence=interfaces.HIGH,
                )

        except InferenceError:
            print("DEBUG (Check): InferenceError occurred.")

    # --- Helper Methods ---

    def _find_ancestor_loop(self, node: nodes.NodeNG) -> nodes.For | nodes.While | None:
        """Walks up the AST from a node to find the first containing loop."""
        current: nodes.NodeNG | None = node
        while current:
            if isinstance(current, (nodes.For, nodes.While)):
                return current
            if isinstance(current, (nodes.FunctionDef, nodes.ClassDef, nodes.Module)):
                return None
            current = current.parent
        return None

    def _is_node_descendant_of(self, node: nodes.NodeNG, ancestor: nodes.NodeNG) -> bool:
        """Checks if `node` is a descendant of or is the same as `ancestor`."""
        # For inferred nodes that aren't part of the main tree (like builtins),
        # they won't have a parent. They are implicitly global.
        if not hasattr(node, "parent"):
            return False

        current: nodes.NodeNG | None = node
        while current:
            if current == ancestor:
                return True
            if isinstance(current, (nodes.FunctionDef, nodes.ClassDef, nodes.Module)):
                break  # Stop at boundaries
            current = current.parent
        return False


def register(linter: PyLinter) -> None:
    """This required function is called by Pylint to register the checker."""
    linter.register_checker(RepeatedIteratorLoopChecker(linter))
