# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import logging  # Added for debugging
from typing import TYPE_CHECKING, Set

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

    name = "repeated-iterator-loop"
    msgs = {
        "W4801": (
            "Iterator '%s' from an outer scope is re-used or consumed in a nested loop.",
            "looping-through-iterator",
            "...",
        )
    }

    options = ()

    KNOWN_ITERATOR_PRODUCING_FUNCTIONS: Set[str] = {
        "map", "filter", "zip", "iter", "reversed"
    }
    KNOWN_ITERATOR_CONSUMING_FUNCTIONS: Set[str] = {
        "list", "tuple", "set", "sorted", "sum", "min", "max", "all", "any", "dict", "zip",
    }

    def _is_node_descendant_of(
            self, node: nodes.NodeNG, ancestor: nodes.NodeNG
    ) -> bool:
        """Checks if `node` is a descendant of or is the same as `ancestor`."""
        current: nodes.NodeNG | None = node
        while current:
            if current == ancestor:
                return True
            if isinstance(current, (nodes.FunctionDef, nodes.ClassDef, nodes.Module)):
                break
            current = current.parent
        return False

    def _check_usage_with_inference(
            self,
            iterator_name_node: nodes.Name,
            usage_context_node: nodes.NodeNG
    ) -> None:
        """
        Checks if the used iterator is defined outside an ancestor loop.
        """
        logging.debug("--- Checking usage of '%s' at line %s ---", iterator_name_node.name, iterator_name_node.lineno)

        # 1. Find the first ancestor `for` or `while` loop.
        parent_walker = usage_context_node.parent
        ancestor_loop_node: nodes.For | nodes.While | None = None
        while parent_walker:
            if isinstance(parent_walker, (nodes.For, nodes.While)):
                ancestor_loop_node = parent_walker
                break
            if isinstance(parent_walker, (nodes.FunctionDef, nodes.ClassDef, nodes.Module)):
                break
            parent_walker = parent_walker.parent

        if not ancestor_loop_node:
            logging.debug("No ancestor For/While loop found. Aborting check.")
            return
        logging.debug("Ancestor loop found: %s", ancestor_loop_node.as_string())

        # 2. Use inference to find where the iterator was defined.
        try:
            inferred_values = list(iterator_name_node.infer())
            logging.debug("Inferred definitions for '%s': %r", iterator_name_node.name, inferred_values)

            if not inferred_values or inferred_values[0] is Uninferable:
                logging.debug("Inference failed or returned Uninferable. Aborting check.")
                return

            # 3. Check if *any* of the possible definitions cause a violation.
            for definition_node in inferred_values:
                logging.debug("... Analyzing definition: %r", definition_node)
                is_iterator_definition = False
                actual_definition_node = definition_node

                if isinstance(definition_node, nodes.GeneratorExp):
                    is_iterator_definition = True
                elif (
                        isinstance(definition_node, nodes.Call)
                        and isinstance(definition_node.func, nodes.Name)
                        and definition_node.func.name in self.KNOWN_ITERATOR_PRODUCING_FUNCTIONS
                ):
                    is_iterator_definition = True
                elif isinstance(definition_node, nodes.AssignName):
                    rhs = definition_node.parent.value
                    if isinstance(rhs, nodes.GeneratorExp):
                        is_iterator_definition = True
                        actual_definition_node = rhs
                    elif (isinstance(rhs, nodes.Call)
                          and isinstance(rhs.func, nodes.Name)
                          and rhs.func.name in self.KNOWN_ITERATOR_PRODUCING_FUNCTIONS):
                        is_iterator_definition = True
                        actual_definition_node = rhs

                if not is_iterator_definition:
                    logging.debug("... Not an iterator definition we track. Continuing.")
                    continue

                logging.debug("... Identified as an iterator definition. Checking position.")
                is_descendant = self._is_node_descendant_of(actual_definition_node, ancestor_loop_node)
                logging.debug("... Is definition a descendant of the loop? %s", is_descendant)

                if not is_descendant:
                    logging.debug(">>> VIOLATION FOUND! Firing message for '%s'!", iterator_name_node.name)
                    self.add_message(
                        "looping-through-iterator",
                        node=iterator_name_node,
                        args=(iterator_name_node.name,),
                    )
                    break
        except InferenceError as e:
            logging.debug("InferenceError occurred: %s. Aborting check.", e)
            return

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_for(self, node: nodes.For) -> None:
        if isinstance(node.iter, nodes.Name):
            self._check_usage_with_inference(node.iter, usage_context_node=node)

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_call(self, node: nodes.Call) -> None:
        if (isinstance(node.func, nodes.Name)
                and node.func.name in self.KNOWN_ITERATOR_CONSUMING_FUNCTIONS):
            for arg in node.args:
                if isinstance(arg, nodes.Name):
                    self._check_usage_with_inference(arg, usage_context_node=node)


def register(linter: PyLinter) -> None:
    linter.register_checker(RepeatedIteratorLoopChecker(linter))