# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from typing import TYPE_CHECKING, Union, Iterable

from astroid import nodes

from pylint import checkers, interfaces
from pylint.checkers import utils

if TYPE_CHECKING:
    from pylint.lint import PyLinter

DefinitionType = nodes.NodeNG | str
LOOP_NODES = (nodes.For, nodes.While, nodes.ListComp, nodes.SetComp, nodes.DictComp, nodes.GeneratorExp)


class RepeatedIteratorLoopChecker(checkers.BaseChecker):
    """Checks for exhaustible iterators that are re-used in a nested loop."""

    name = "looping-through-iterator"
    msgs = {
        "W4801": (
            "Iterator '%s' from an outer scope is re-used or consumed in a nested loop.",
            "looping-through-iterator",
            "...",
        )
    }

    options = ()

    KNOWN_ITERATOR_PRODUCING_FUNCTIONS: set[str] = {
        "builtins.map",
        "builtins.filter",
        "builtins.zip",
        "builtins.iter",
        "builtins.reversed",
    }

    def __init__(self, linter: PyLinter | None = None) -> None:
        super().__init__(linter)
        self._scope_stack: list[dict[str, DefinitionType]] = []

    def visit_module(self, node: nodes.Module) -> None:
        self._scope_stack = [{}]

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        self._scope_stack.append({})

    def leave_functiondef(self, node: nodes.FunctionDef) -> None:
        self._scope_stack.pop()

    def visit_for(self, node: nodes.For) -> None:
        for target in node.target.nodes_of_class(nodes.AssignName):
            self._scope_stack[-1][target.name] = "SAFE"
        self._scope_stack.append({})
        if isinstance(node.iter, nodes.Name):
            self._check_variable_usage(node.iter)

    def leave_for(self, node: nodes.For) -> None:
        self._scope_stack.pop()

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_assign(self, node: nodes.Assign) -> None:
        value_node = node.value
        is_iterator_definition = False
        if isinstance(value_node, nodes.GeneratorExp):
            is_iterator_definition = True
        elif isinstance(value_node, nodes.Call):
            inferred_func = utils.safe_infer(value_node.func)
            if inferred_func and hasattr(inferred_func, "qname"):
                if inferred_func.qname() in self.KNOWN_ITERATOR_PRODUCING_FUNCTIONS:
                    is_iterator_definition = True
        current_scope = self._scope_stack[-1]
        for target in node.targets:
            if isinstance(target, nodes.AssignName):
                variable_name = target.name
                if is_iterator_definition:
                    current_scope[variable_name] = value_node
                else:
                    current_scope[variable_name] = "SAFE"

    @utils.only_required_for_messages("looping-through-iterator")
    def visit_call(self, node: nodes.Call) -> None:
        for arg in node.args:
            if isinstance(arg, nodes.Name):
                self._check_variable_usage(arg)

    def _has_unconditional_exit(self, statements: list[nodes.NodeNG]) -> bool:
        for stmt in statements:
            if isinstance(stmt, (nodes.Return, nodes.Break, nodes.Raise)):
                return True
            if isinstance(stmt, nodes.If):
                if stmt.orelse and self._has_unconditional_exit(
                        stmt.body
                ) and self._has_unconditional_exit(stmt.orelse):
                    return True
            if isinstance(stmt, nodes.Try):
                if stmt.finalbody and self._has_unconditional_exit(stmt.finalbody):
                    return True
                if not stmt.handlers:
                    continue
                try_body_exits = self._has_unconditional_exit(stmt.body)
                if not try_body_exits:
                    continue
                all_handlers_exit = all(
                    self._has_unconditional_exit(handler.body) for handler in stmt.handlers
                )
                if all_handlers_exit:
                    if stmt.orelse:
                        if self._has_unconditional_exit(stmt.orelse):
                            return True
                    else:
                        return True
        return False

    def _is_used_outside_nested_node(
            self, outer_loop: nodes.For | nodes.While,
            nested_node: nodes.NodeNG,
            iterator_name: str
    ) -> bool:
        for node in outer_loop.nodes_of_class(nodes.Name):
            if node.name == iterator_name:
                parent = node.parent
                while parent and parent is not outer_loop:
                    if parent is nested_node:
                        break
                    parent = parent.parent
                else:
                    return True
        return False

    def _check_variable_usage(self, usage_node: nodes.Name) -> None:
        iterator_name = usage_node.name
        definition = None
        for scope in reversed(self._scope_stack):
            if iterator_name in scope:
                definition = scope[iterator_name]
                break
        if not definition or definition == "SAFE":
            return

        ancestor_loops = list(self._get_ancestor_loops(usage_node))
        if len(ancestor_loops) < 2:
            return

        definition_loop = self._find_ancestor_loop(definition)
        if definition_loop in ancestor_loops:
            return

        inner_loop = ancestor_loops[0]
        outer_loop = ancestor_loops[1]

        # FINAL FIX: The logic must be combined. We must check for the "parser"
        # pattern BEFORE we check for other unconditional exits.
        is_in_next_call = (
                isinstance(usage_node.parent, nodes.Call) and
                isinstance(usage_node.parent.func, nodes.Name) and
                usage_node.parent.func.name == "next"
        )
        if is_in_next_call:
            if not self._is_used_outside_nested_node(outer_loop, inner_loop, iterator_name):
                # This is the "parser" pattern. It's safe. Do not proceed.
                return

        if not isinstance(outer_loop, (nodes.For, nodes.While)):
            return

        try:
            # For a 'for' loop, the inner loop must be in its body.
            inner_loop_index = outer_loop.body.index(inner_loop)
            statements_after_inner_loop = outer_loop.body[inner_loop_index + 1:]
            if self._has_unconditional_exit(statements_after_inner_loop):
                return
        except (AttributeError, ValueError):
            # For a 'while' loop or other structure, we may not have a simple body list.
            # We can check the whole body for an exit. A bit less precise but safe.
            if self._has_unconditional_exit(outer_loop.body):
                return

        self.add_message(
            "looping-through-iterator",
            node=usage_node,
            args=(iterator_name,),
            confidence=interfaces.HIGH,
        )

    def _find_ancestor_loop(self, node: nodes.NodeNG) -> LOOP_NODES | None:
        current = node.parent
        while current:
            if isinstance(current, LOOP_NODES):
                return current
            if isinstance(current, (nodes.FunctionDef, nodes.ClassDef, nodes.Module)):
                return None
            current = current.parent
        return None

    def _get_ancestor_loops(self, node: nodes.NodeNG) -> Iterable[LOOP_NODES]:
        current = node
        while (ancestor := self._find_ancestor_loop(current)) is not None:
            yield ancestor
            current = ancestor


def register(linter: PyLinter) -> None:
    linter.register_checker(RepeatedIteratorLoopChecker(linter))