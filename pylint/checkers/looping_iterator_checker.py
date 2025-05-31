# pylint: disable=too-many-ancestors
# (BaseChecker has many ancestors)

"""
Pylint checker for detecting repeated looping through exhaustible iterators.
"""
from pylint.checkers import BaseChecker
from pylint.checkers.utils import is_builtin_object  # For more robust builtin checks
from astroid import nodes
import logging

# Initialize logging (you might want to configure this more elaborately)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class RepeatedlyLoopingIteratorChecker(BaseChecker):
    """
    Checks for repeatedly looping through the same exhaustible iterator instance.
    """

    name = "repeated_iterator_checker"
    MSG_ID = "W4801"
    msgs = {
        MSG_ID: (
            "Repeatedly looping through exhaustible iterator '%s'. "
            "The iterator will be exhausted after the first complete loop.",
            "looping-through-iterator",
            "Emitted when an exhaustible iterator is looped over multiple times.",
        )
    }
    options = ()

    # Known function names
    KNOWN_EXHAUSTIBLE_FUNCS = {'map', 'filter', 'zip', 'iter', 'reversed'}
    KNOWN_REITERABLE_CONSUMERS = {'list', 'tuple', 'set', 'sorted', 'dict'}

    def __init__(self, linter=None):
        super().__init__(linter)
        # _iterator_definitions:
        #   key: (scope_node, variable_name_str) for a variable
        #   value: {
        #       'assign_node': nodes.AssignName, # The AssignName node for this variable's definition
        #       'usage_state': dict             # Shared dict: {'is_exhaustible': bool, 'first_for_node_id': int | None}
        #   }
        self._iterator_definitions = {}
        self._current_for_loops = []
        logging.debug("RepeatedlyLoopingIteratorChecker initialized")

    # Helper to check if a node is a descendant of another
    def is_node_descendant_of(node: nodes.NodeNG, ancestor_candidate: nodes.NodeNG) -> bool:
        """
        Check if `node` is a descendant of `ancestor_candidate`.
        """
        logging.debug(f"Checking if {node} is descendant of {ancestor_candidate}")
        parent = node
        while parent:
            if parent == ancestor_candidate:
                logging.debug(f"{node} is a descendant of {ancestor_candidate}")
                return True
            if not hasattr(parent, 'parent') or parent.parent is parent:
                break
            parent = parent.parent
        logging.debug(f"{node} is not a descendant of {ancestor_candidate}")
        return False

    def visit_module(self, _: nodes.Module) -> None:
        """Clear data for every module."""
        logging.debug("visit_module: Clearing iterator definitions and current for loops")
        self._iterator_definitions.clear()
        self._current_for_loops.clear()

    def _is_exhaustible_iterator_producer(self, value_node: nodes.NodeNG) -> bool:
        """
        Determines if a node *directly* produces an exhaustible iterator
        or a re-iterable collection that consumes an iterator.
        """
        logging.debug(f"_is_exhaustible_iterator_producer: Checking {value_node}")

        if isinstance(value_node, nodes.GeneratorExp):
            logging.debug(f"{value_node} is a GeneratorExp, returning True")
            return True

        if not isinstance(value_node, nodes.Call):
            logging.debug(f"{value_node} is not a Call, returning False")
            return False

        # At this point, value_node is a Call node.
        # Try inference first for builtins
        try:
            inferred_func = next(value_node.func.infer(), None)
            logging.debug(f"Inferred function: {inferred_func}")
            if inferred_func and isinstance(inferred_func, nodes.FunctionDef):
                if is_builtin_object(inferred_func):
                    func_name = inferred_func.name
                    logging.debug(f"Builtin function name: {func_name}")
                    if func_name in self.KNOWN_EXHAUSTIBLE_FUNCS:
                        logging.debug(f"{func_name} is in KNOWN_EXHAUSTIBLE_FUNCS, returning True")
                        return True
                    if func_name in self.KNOWN_REITERABLE_CONSUMERS:
                        logging.debug(f"{func_name} is in KNOWN_REITERABLE_CONSUMERS, returning False")
                        return False  # e.g., list(iterator) is not an exhaustible iterator itself
                    # If it's a known builtin but not in these specific lists,
                    # let it fall through to the general name check or default to False.
        except nodes.InferenceError:
            # Inference failed, proceed to name check as a fallback
            logging.debug("Inference failed, proceeding to name check")
            pass

        # Fallback to checking the direct name if inference didn't confirm, or failed
        if isinstance(value_node.func, nodes.Name):
            func_name = value_node.func.name
            logging.debug(f"Function name: {func_name}")
            if func_name in self.KNOWN_EXHAUSTIBLE_FUNCS:
                logging.debug(f"{func_name} is in KNOWN_EXHAUSTIBLE_FUNCS, returning True")
                return True
            if func_name in self.KNOWN_REITERABLE_CONSUMERS:  # list(), tuple() etc.
                logging.debug(f"{func_name} is in KNOWN_REITERABLE_CONSUMERS, returning False")
                return False

        logging.debug(f"{value_node} is not an exhaustible iterator producer, returning False")
        return False  # Default: not an exhaustible iterator producer we've identified

    def visit_assign(self, node: nodes.Assign) -> None:
        """
        Tracks assignments. If a variable is assigned an exhaustible iterator,
        or aliases an existing one, its state is tracked.
        Reassigning a variable to a new iterator or a non-iterator updates its state.
        """
        logging.debug(f"visit_assign: Processing assignment {node}")
        value_node = node.value  # RHS of the assignment

        determined_shared_usage_state = None

        is_producer_exhaustible = self._is_exhaustible_iterator_producer(value_node)
        logging.debug(f"Is producer exhaustible: {is_producer_exhaustible}")

        if is_producer_exhaustible:
            # RHS is a new exhaustible iterator instance (e.g., x = (gen exp) or x = map(...))
            determined_shared_usage_state = {
                'is_exhaustible': True,
                'first_for_node_id': None,
            }
            logging.debug(f"New exhaustible iterator, usage state: {determined_shared_usage_state}")
        elif isinstance(value_node, nodes.Name):  # RHS is a variable name (e.g., y = x)
            source_var_name_node = value_node
            logging.debug(f"RHS is a variable name: {source_var_name_node.name}")
            try:
                source_def_nodes = source_var_name_node.lookup(source_var_name_node.name)[1]
                if source_def_nodes:
                    source_def_node = source_def_nodes[0]
                    if isinstance(source_def_node, (nodes.AssignName, nodes.Arguments)):
                        key_for_source_var_def = (source_def_node.scope(), source_def_node.name)
                        logging.debug(f"Key for source var def: {key_for_source_var_def}")

                        if key_for_source_var_def in self._iterator_definitions:
                            source_var_entry = self._iterator_definitions[key_for_source_var_def]
                            # Only share state if the source is itself marked as exhaustible
                            if source_var_entry['usage_state']['is_exhaustible']:
                                determined_shared_usage_state = source_var_entry['usage_state']
                                logging.debug(f"Sharing usage state: {determined_shared_usage_state}")
            except (nodes.InferenceError, IndexError, Exception):
                logging.debug("Error during inference or lookup")
                pass
        # If determined_shared_usage_state is still None here, it means the RHS is not
        # a new exhaustible iterator, nor an alias to a known one.
        # It could be a non-exhaustible value (e.g. list(), or a number).
        # In this case, the target variable should not be tracked as exhaustible,
        # or should be un-tracked if it was before.

        for target_node in node.targets:
            if isinstance(target_node, nodes.AssignName):
                var_key = (target_node.scope(), target_node.name)
                logging.debug(f"Target variable key: {var_key}")
                if determined_shared_usage_state:
                    # Variable is now an exhaustible iterator (or an alias to one)
                    self._iterator_definitions[var_key] = {
                        'assign_node': target_node,
                        'usage_state': determined_shared_usage_state
                    }
                    logging.debug(f"Updated iterator definitions: {self._iterator_definitions}")
                else:
                    # Variable is assigned a non-exhaustible value or an untracked one.
                    # If it was previously tracked as exhaustible, remove it.
                    if var_key in self._iterator_definitions:
                        del self._iterator_definitions[var_key]
                        logging.debug(f"Removed variable from iterator definitions: {self._iterator_definitions}")

    def _check_expr_for_iterator_reuse(self, expr_node: nodes.NodeNG, current_for_node: nodes.For) -> None:
        """
        Checks an expression used in a for loop for iterator reuse.
        """
        logging.debug(f"_check_expr_for_iterator_reuse: Checking {expr_node} in for loop {current_for_node}")
        if isinstance(expr_node, nodes.Name):
            iterator_name_str = expr_node.name
            logging.debug(f"Expression is a name: {iterator_name_str}")

            try:
                inferred_defs = expr_node.lookup(iterator_name_str)[1]
            except (nodes.InferenceError, IndexError, Exception):
                logging.debug("Error during inference or lookup")
                return

            if not inferred_defs or not isinstance(inferred_defs[0], (nodes.AssignName, nodes.Arguments)):
                logging.debug("No inferred definitions or not an AssignName/Arguments")
                return

            var_def_node = inferred_defs[0]
            key_for_var_def = (var_def_node.scope(), var_def_node.name)
            logging.debug(f"Key for variable definition: {key_for_var_def}")

            if key_for_var_def in self._iterator_definitions:
                iter_entry = self._iterator_definitions[key_for_var_def]
                shared_usage_state = iter_entry['usage_state']
                logging.debug(f"Iterator entry found: {iter_entry}")

                # Check if the state itself indicates it's an exhaustible iterator
                if not shared_usage_state.get('is_exhaustible', False):  # Defensive get
                    logging.debug("Not an exhaustible iterator")
                    return

                assign_node_of_iterated_var = iter_entry['assign_node']
                definition_statement_node = assign_node_of_iterated_var.statement()

                if shared_usage_state['first_for_node_id'] is None:
                    shared_usage_state['first_for_node_id'] = id(current_for_node)
                    logging.debug(f"First for loop, set node id: {shared_usage_state['first_for_node_id']}")
                else:
                    if id(current_for_node) == shared_usage_state['first_for_node_id']:
                        if len(self._current_for_loops) > 1:
                            parent_loop_node = self._current_for_loops[-2]
                            if not is_node_descendant_of(definition_statement_node, parent_loop_node):
                                self.add_message(
                                    self.MSG_ID,
                                    node=expr_node,
                                    args=(iterator_name_str,),
                                )
                                logging.warning(f"Repeated loop in different branch detected for {iterator_name_str}")
                    else:
                        self.add_message(
                            self.MSG_ID,
                            node=expr_node,
                            args=(iterator_name_str,),
                        )
                        logging.warning(f"Repeated loop detected for {iterator_name_str}")

        elif isinstance(expr_node, nodes.Call):
            try:
                inferred_func = next(expr_node.func.infer(), None)
                func_name_to_check = None
                if inferred_func and isinstance(inferred_func, nodes.FunctionDef) and is_builtin_object(inferred_func):
                    func_name_to_check = inferred_func.name
                elif isinstance(expr_node.func, nodes.Name):
                    func_name_to_check = expr_node.func.name

                if func_name_to_check in ('zip', 'map', 'filter'):  # Only recurse for these specific funcs
                    for arg_expr in expr_node.args:
                        self._check_expr_for_iterator_reuse(arg_expr, current_for_node)
                    for kwarg_node in expr_node.keywords:  # type: ignore[attr-defined]
                        self._check_expr_for_iterator_reuse(kwarg_node.value, current_for_node)
            except (nodes.InferenceError, AttributeError):
                logging.debug("Error during inference or attribute access in Call node")
                pass

    def visit_for(self, node: nodes.For) -> None:
        logging.debug(f"visit_for: Entering for loop {node}")
        self._current_for_loops.append(node)
        self._check_expr_for_iterator_reuse(node.iter, node)

    def leave_for(self, _: nodes.For) -> None:
        logging.debug("leave_for: Leaving for loop")
        if self._current_for_loops:
            self._current_for_loops.pop()
            logging.debug(f"Current for loops: {self._current_for_loops}")


def register(linter):
    linter.register_checker(RepeatedlyLoopingIteratorChecker(linter))
    logging.debug("Checker registered")