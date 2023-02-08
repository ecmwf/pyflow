from __future__ import absolute_import

import functools
import operator


class Overloaded:
    def make_expression(self):
        return NodeName(self)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __nonzero__(self):
        return self.__bool__()

    def __bool__(self):
        raise ValueError(
            "You cannot use 'and', 'or' and 'not' in trigger expressions. Use '&', '|' and '~' instead"
        )

    def __len__(self):
        raise NotImplementedError("__len__ not implemented for", self)

    def __invert__(self):
        return Not(self)

    def __eq__(self, other):
        return Eq(self, other)

    def __ne__(self, other):
        return Ne(self, other)

    def __lt__(self, other):
        return Lt(self, other)

    def __le__(self, other):
        return Le(self, other)

    def __gt__(self, other):
        return Gt(self, other)

    def __ge__(self, other):
        return Ge(self, other)

    def __sub__(self, other):
        raise NotImplementedError("__sub__ not implemented for", self)

    def __add__(self, other):
        raise NotImplementedError("__add__ not implemented for", self)

    def __mul__(self, other):
        raise NotImplementedError("__mul__ not implemented for", self)

    def __div__(self, other):
        return Div(self, other)

    def __matmul__(self, other):
        raise NotImplementedError("__matmul__ not implemented for", self)

    def __truediv__(self, other):
        raise NotImplementedError("__truediv__ not implemented for", self)

    def __floordiv__(self, other):
        raise NotImplementedError("__floordiv__ not implemented for", self)

    def __mod__(self, other):
        return Mod(self, other)

    def __divmod__(self, other):
        raise NotImplementedError("__divmod__ not implemented for", self)

    def __pow__(self, other):
        raise NotImplementedError("__pow__ not implemented for", self)

    def __lshift__(self, other):
        raise NotImplementedError("__lshift__ not implemented for", self)

    def __rshift__(self, other):
        raise NotImplementedError("__rshift__ not implemented for", self)

    def __xor__(self, other):
        raise NotImplementedError("__xor__ not implemented for", self)

    def __radd__(self, other):
        raise NotImplementedError("__radd__ not implemented for", self)

    def __rsub__(self, other):
        raise NotImplementedError("__rsub__ not implemented for", self)

    def __rmul__(self, other):
        raise NotImplementedError("__rmul__ not implemented for", self)

    def __rmatmul__(self, other):
        raise NotImplementedError("__rmatmul__ not implemented for", self)

    def __rtruediv__(self, other):
        raise NotImplementedError("__rtruediv__ not implemented for", self)

    def __rfloordiv__(self, other):
        raise NotImplementedError("__rfloordiv__ not implemented for", self)

    def __rmod__(self, other):
        raise NotImplementedError("__rmod__ not implemented for", self)

    def __rdivmod__(self, other):
        raise NotImplementedError("__rdivmod__ not implemented for", self)

    def __rpow__(self, other):
        raise NotImplementedError("__rpow__ not implemented for", self)

    def __rlshift__(self, other):
        raise NotImplementedError("__rlshift__ not implemented for", self)

    def __rrshift__(self, other):
        raise NotImplementedError("__rrshift__ not implemented for", self)

    def __rand__(self, other):
        from .nodes import NodeAdder

        if isinstance(other, NodeAdder):
            return other.add_and(self)
        raise NotImplementedError("__rand__ not implemented for", self)

    def __rxor__(self, other):
        raise NotImplementedError("__rxor__ not implemented for", self)

    def __ror__(self, other):
        from .nodes import NodeAdder

        if isinstance(other, NodeAdder):
            return other.add_or(self)
        raise NotImplementedError("__ror__ not implemented for", self)

    def __iadd__(self, other):
        raise NotImplementedError("__iadd__ not implemented for", self)

    def __isub__(self, other):
        raise NotImplementedError("__isub__ not implemented for", self)

    def __imul__(self, other):
        raise NotImplementedError("__imul__ not implemented for", self)

    def __imatmul__(self, other):
        raise NotImplementedError("__imatmul__ not implemented for", self)

    def __itruediv__(self, other):
        raise NotImplementedError("__itruediv__ not implemented for", self)

    def __ifloordiv__(self, other):
        raise NotImplementedError("__ifloordiv__ not implemented for", self)

    def __imod__(self, other):
        raise NotImplementedError("__imod__ not implemented for", self)

    def __ipow__(self, other):
        raise NotImplementedError("__ipow__ not implemented for", self)

    def __ilshift__(self, other):
        raise NotImplementedError("__ilshift__ not implemented for", self)

    def __irshift__(self, other):
        raise NotImplementedError("__irshift__ not implemented for", self)

    def __iand__(self, other):
        raise NotImplementedError("__iand__ not implemented for", self)

    def __ixor__(self, other):
        raise NotImplementedError("__ixor__ not implemented for", self)

    def __ior__(self, other):
        raise NotImplementedError("__ior__ not implemented for", self)

    def __neg__(self):
        raise NotImplementedError("__neg__ not implemented for", self)

    def __pos__(self):
        raise NotImplementedError("__pos__ not implemented for", self)

    def __abs__(self):
        raise NotImplementedError("__abs__ not implemented for", self)


UNDEFINED = object()


class Expression(Overloaded):
    def make_expression(self):
        return self

    def simplify(self):
        return self._simplify()

    def _simplify(self):
        return self

    def evaluate(self):
        return UNDEFINED


class Deferred(Expression):
    """
    Defines an expression which will be evaluated only at suite generation time.

    Parameters:
        func(function): The callback function to generate the expression.
        *args(tuple): Accept extra positional arguments for the callback function.

    Example::

        def my_callback(var, val):
            pass

        pyflow.Deferred(my_callback, 'foo', 'bar')
    """

    def __init__(self, func, *args):
        self._func = func
        self._args = args

    def generate_expression(self, parent=None):
        """
        Generates the expression.

        Parameters:
            parent(*Node*): The parent node to generate the expression for.

        Returns:
            *expression*: Generated expression.
        """
        return self._func(*self._args).generate_expression(parent)


class BinOp(Expression):
    def __init__(self, op, left, right, priority):
        self._op = op
        self._left = make_expression(left)
        self._right = make_expression(right)
        self._priority = priority

    def generate_expression(self, parent=None):
        expr1 = self._left.generate_expression(parent)
        if self._priority >= self._left._priority:
            expr1 = "(%s)" % expr1

        expr2 = self._right.generate_expression(parent)
        if self._priority >= self._right._priority:
            expr2 = "(%s)" % expr2

        return "%s %s %s" % (expr1, self._op, expr2)

    def __repr__(self):
        return "(%r %s %r)" % (self._left, self._op, self._right)

    def _graph(self, dot, parent):
        self._left._graph(dot, parent)
        self._right._graph(dot, parent)

    def simplify(self):
        self._left = self._left.simplify()
        self._right = self._right.simplify()
        return self._simplify()


class Ne(BinOp):
    def __init__(self, left, right):
        super().__init__("ne", left, right, 1)


class Le(BinOp):
    def __init__(self, left, right):
        super().__init__("le", left, right, 1)


class Ge(BinOp):
    def __init__(self, left, right):
        super().__init__("ge", left, right, 1)


class Lt(BinOp):
    def __init__(self, left, right):
        super().__init__("lt", left, right, 1)


class Gt(BinOp):
    def __init__(self, left, right):
        super().__init__("gt", left, right, 1)


class Eq(BinOp):
    def __init__(self, left, right):
        super().__init__("eq", left, right, 1)


class Or(BinOp):
    def __init__(self, left, right):
        super().__init__("or", left, right, 0)

    def _simplify(self):
        (l, r) = (self._left.evaluate(), self._right.evaluate())

        if l is not UNDEFINED and r is not UNDEFINED:
            return self._left.value or self._right.value

        if l is not UNDEFINED:
            if l is False:
                return self._right

            if l is True:
                return Constant(True)

        if r is not UNDEFINED:
            if r is False:
                return self._left

            if r is True:
                return Constant(True)

        return self


class And(BinOp):
    def __init__(self, left, right):
        super().__init__("and", left, right, 0)

    def _simplify(self):
        (l, r) = (self._left.evaluate(), self._right.evaluate())

        if l is not UNDEFINED and r is not UNDEFINED:
            return self._left.value and self._right.value

        if l is not UNDEFINED:
            if l is True:
                return self._right

            if l is False:
                return Constant(False)

        if r is not UNDEFINED:
            if r is True:
                return self._left

            if r is False:
                return Constant(False)

        return self


class Sub(BinOp):
    def __init__(self, left, right):
        super().__init__("-", left, right, 2)


class Add(BinOp):
    def __init__(self, left, right):
        super().__init__("+", left, right, 2)


class Mod(BinOp):
    def __init__(self, left, right):
        super().__init__("%", left, right, 3)


class Div(BinOp):
    def __init__(self, left, right):
        super().__init__("/", left, right, 3)


class Atom(Expression):
    _priority = 99


class NodeStatus(Atom):
    def __init__(self, status):
        self._status = status

    def generate_expression(self, parent=None):
        return str(self._status)

    def __repr__(self):
        return self._status

    def _graph(self, dot, parent):
        pass


class NodeName(Atom):
    def __init__(self, node):
        self._node = node

    def make_expression(self):
        return self

    def generate_expression(self, parent=None):
        return self._node.relative_path(parent)

    def __repr__(self):
        return self._node.fullname

    def _graph(self, dot, parent):
        dot.edge(parent, self._node)


class Constant(Atom):
    def __init__(self, value):
        self._value = value

    def generate_expression(self, parent=None):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def _graph(self, dot, parent):
        pass

    def evaluate(self):
        return self._value


class Function(Atom):
    def __init__(self, name, param):
        self._name = name
        self._param = make_expression(param)

    def generate_expression(self, parent=None):
        return "%s(%s)" % (self._name, self._param.generate_expression(parent))

    def _graph(self, dot, parent):
        self._param._graph(dot, parent)

    def __repr__(self):
        return "%s(%r)" % (self._name, self._param)


class Not(Atom):
    def __init__(self, param):
        self._param = make_expression(param)

    def generate_expression(self, parent=None):
        return "not (%s)" % (self._param.generate_expression(parent),)

    def _graph(self, dot, parent):
        self._param._graph(dot, parent)

    def __repr__(self):
        return "not (%r)" % (self._param,)


def make_expression(e):
    if isinstance(e, str):
        return NodeStatus(e)

    if isinstance(e, int):
        return Constant(e)

    return e.make_expression()


def binop(cls):
    def wrapped(op, e):
        return cls(expression_from_json(e[0]), expression_from_json(e[1]))

    return wrapped


def unop(cls):
    def wrapped(op, e):
        return cls(expression_from_json(e))

    return wrapped


def status(op, e):
    return Eq(NodeStatus(e), NodeStatus(op))


JSON_FACTORIES = {
    "or": binop(Or),
    "|": binop(Or),
    "and": binop(And),
    "&": binop(And),
    "eq": binop(Eq),
    "==": binop(Eq),
    "ne": binop(Ne),
    "!=": binop(Ne),
    "lt": binop(Lt),
    "<": binop(Lt),
    "le": binop(Le),
    "<=": binop(Le),
    "gt": binop(Gt),
    ">": binop(Gt),
    "ge": binop(Ge),
    ">=": binop(Ge),
    "mod": binop(Mod),
    "%": binop(Mod),
    "div": binop(Div),
    "/": binop(Div),
    "not": unop(Not),
    "~": unop(Not),
    "complete": status,
    "unknown": status,
    "aborted": status,
    "submitted": status,
    "suspended": status,
    "active": status,
    "queued": status,
}


def expression_from_json(e):
    op = e.keys()
    assert len(op) == 1
    op = next(iter(op))
    args = e[op]

    if isinstance(args, tuple):
        return JSON_FACTORIES[op](op, *args)
    else:
        return JSON_FACTORIES[op](op, args)


def all_complete(nodes):
    """
    Returns a trigger expression for all of the supplied nodes being complete.

    Parameters:
        nodes(list): The list of input nodes.

    Returns:
        *expression*: Trigger expression for all of the supplied nodes being complete.

    Example::

        trigger = pyflow.all_complete(pyflow.Task('task-{}'.format(i)) for i in range(10))
    """

    if not nodes:
        raise ValueError("cannot wait on an empty list of nodes")

    return functools.reduce(operator.and_, nodes)


def sequence(nodes):
    """
    Sets triggers so that the input tasks/families will run in sequence, in the order that they are given.

    The input nodes are modified in-place. Existing triggers will be preserved by &-ing them with the new trigger.

    Parameters:
        nodes(list): The list of input nodes.

    Example::

        pyflow.sequence(pyflow.Task('{}_{}'.format(name, i), i) for i in range(counters))
    """

    if not nodes:
        # Attempting to sequence 0 nodes is an error.
        raise ValueError("cannot sequence an empty list of nodes")

    # Apply right-shift to the nodes to add sequential triggers.
    functools.reduce(operator.rshift, nodes)
