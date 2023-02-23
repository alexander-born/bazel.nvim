import ast
from copy import copy
from functools import total_ordering
from label import parse_label, resolve_label


def first(xs):
    for x in xs:
        if x:
            return x
    return None


def end(x):
    return x.end if x else None


def start(x):
    return x.start if x else None


@total_ordering
class Cursor:
    def __init__(self, row, col):
        self.row = row
        self.col = col

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def __lt__(self, other):
        if self.row < other.row:
            return True
        if self.row > other.row:
            return False
        return self.col < other.col

    def __add__(self, cols):
        return Cursor(row=self.row, col=self.col + cols)


class Reference:
    def __init__(self, label, cursor):
        self.label = label
        self.cursor = cursor


class Targets(dict):
    def __missing__(self, key):
        # TODO not relevant yet because we don't ever enter rule names into the environment, so all lookups fail.
        # print(f"undefined target: {repr(key)}")
        return "undefined"


class Bindings(dict):
    def __init__(self, d=None):
        if d is None:
            d = {}
        # print(f"init: {d}")
        super(Bindings, self).__init__(d)

    def __setitem__(self, key, value):
        print(f"set {key} = {value}")
        return super(Bindings, self).__setitem__(key, value)

    def __getitem__(self, key):
        print(f"lookup {key}")
        return super(Bindings, self).__getitem__(key)

    def __missing__(self, key):
        print(f"undefined binding: {key}")
        # ipdb.set_trace()
        return "undefined"


class Environment:
    def __init__(self, label, workspace_root, targets=Targets(), bindings=Bindings()):
        self.label = label
        self.workspace_root = workspace_root
        self.targets = targets
        self.bindings = bindings


# We keep "covers" and "get_thing_at" seperate because we can stop searching
# when "covers" returns true even if "get_thing_at" returned None.


class File:
    def __init__(self, stmts):
        self.stmts = stmts

    def covers(self, cursor):
        if not self.stmts:
            return False
        return self.stmts[0].start <= cursor and cursor < self.stmts[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for stmt in self.stmts:
            if stmt.covers(cursor):
                return stmt.get_thing_at(cursor)


class DefStmt:
    def __init__(self, name, parameters, suite):
        self.name = name
        self.parameters = parameters
        self.suite = suite
        self.start = start(first([parameters, suite]))
        self.end = end(first([suite, parameters]))

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.name.covers(cursor):
            return self.name
        if self.parameters.covers(cursor):
            return self.parameters.get_thing_at(cursor)
        return self.suite.get_thing_at(cursor)


class Parameters:
    def __init__(self, parameters):
        self.parameters = parameters
        self.start = start(first(self.parameters))
        self.end = end(first(self.parameters[::-1]))

    def __len__(self):
        return len(self.parameters)

    def covers(self, cursor):
        if not self.parameters:
            return False
        return self.parameters[0].start <= cursor and cursor < self.parameters[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for parameter in self.parameters:
            if parameter.covers(cursor):
                return parameter.get_thing_at(cursor)


class VarParameter:
    def __init__(self, identifier):
        self._identifier = identifier
        self.start = identifier.start
        self.end = identifier.end

    def identifier(self):
        return self._identifier.identifier

    def reference(self):
        return self._identifier.reference

    def covers(self, cursor):
        return self._identifier.covers(cursor)

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self._identifier.get_thing_at(cursor)


class KwParameter:
    def __init__(self, identifier):
        self._identifier = identifier
        self.start = identifier.start
        self.end = identifier.end

    def identifier(self):
        return self._identifier.identifier

    def reference(self):
        return self._identifier.reference

    def covers(self, cursor):
        return self._identifier.covers(cursor)

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self._identifier.get_thing_at(cursor)


class ParameterWithDefault:
    def __init__(self, identifier, default):
        self._identifier = identifier
        self.default = default
        self.start = identifier.start
        self.end = default.end

    def identifier(self):
        return self._identifier.identifier

    def reference(self):
        return self._identifier.reference

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self._identifier.covers(cursor):
            return self._identifier.get_thing_at(cursor)
        return self.default.get_thing_at(cursor)


class IfStmt:
    def __init__(self, test, body, orelse):
        self.test = test
        self.body = body
        self.orelse = orelse
        self.start = self.test.start
        self.end = end(first([orelse, body, test]))

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.test.covers(cursor):
            return self.test.get_thing_at(cursor)
        if self.body.covers(cursor):
            return self.body.get_thing_at(cursor)
        assert self.orelse.covers(cursor)
        return self.orelse.get_thing_at(cursor)


class ForStmt:
    def __init__(self, target, iterable, body):
        self.target = target
        self.iterable = iterable
        self.body = body
        self.start = self.target.start
        self.end = end(first([body, iterable]))

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.target.covers(cursor):
            return self.target.get_thing_at(cursor)
        if self.iterable.covers(cursor):
            return self.iterable.get_thing_at(cursor)
        assert self.body.covers(cursor)
        return self.body.get_thing_at(cursor)


class Suite:
    def __init__(self, stmts):
        self.stmts = stmts
        self.start = start(first(stmts))
        self.end = end(first(stmts[::-1]))

    def __len__(self):
        return len(self.stmts)

    def covers(self, cursor):
        if not self.stmts:
            return False
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for stmt in self.stmts:
            if stmt.covers(cursor):
                return stmt.get_thing_at(cursor)


class SimpleStmt:
    def __init__(self):
        raise Exception("Not Implemented Yet")

    def __len__(self):
        return len(self.stmts)


class ReturnStmt:
    def __init__(self, value):
        self.value = value
        self.start = start(value)
        self.end = end(value)

    def covers(self, cursor):
        if not self.value:
            return False
        return self.value.covers(cursor)

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self.value.get_thing_at(cursor)


class BreakStmt:
    def __init__(self):
        self.start = None
        self.end = None


class ContinueStmt:
    def __init__(self):
        self.start = None
        self.end = None


class PassStmt:
    def __init__(self):
        self.start = None
        self.end = None


class AssignStmt:
    def __init__(self, targets, value, op=None):
        self.targets = targets
        self.value = value
        self.op = op
        self.start = targets.start
        self.end = value.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.targets.covers(cursor):
            return self.targets.get_thing_at(cursor)
        assert self.value.covers(cursor)
        return self.value.get_thing_at(cursor)


class ExprStmt:
    def __init__(self):
        raise Exception("Not Implemented Yet")


class Expression:
    def __init__(self, tests):
        self.tests = tests
        self.start = start(first(tests))
        self.end = end(first(tests[::-1]))

    def __len__(self):
        return len(self.tests)

    def covers(self, cursor):
        if not self.tests:
            return False
        return self.tests[0].start <= cursor and cursor < self.tests[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for argument in self.tests:
            if argument.covers(cursor):
                return argument.get_thing_at(cursor)


class IfExpr:
    def __init__(self, test, body, orelse):
        self.test = test
        self.body = body
        self.orelse = orelse
        self.start = self.test.start
        self.end = end(first([orelse, body, test]))

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.test.covers(cursor):
            return self.test.get_thing_at(cursor)
        if self.body.covers(cursor):
            return self.body.get_thing_at(cursor)
        assert self.orelse.covers(cursor)
        return self.orelse.get_thing_at(cursor)


class PrimaryExprWithCallSuffix:
    def __init__(self, primary_expr, arguments):
        self.primary_expr = primary_expr
        self.arguments = arguments
        self.start = primary_expr.start
        self.end = end(first([arguments, primary_expr]))

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.primary_expr.covers(cursor):
            return self.primary_expr.get_thing_at(cursor)
        return self.arguments.get_thing_at(cursor)


class PrimaryExprWithDotSuffix:
    # attribute has no Cursor in ast
    def __init__(self, value, attribute):
        self.value = value
        self.attribute = attribute
        self.start = value.start
        self.end = value.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self.value.get_thing_at(cursor)


class IndexExpr:
    def __init__(self, index):
        self.index = index
        self.start = index.start
        self.end = index.end

    def covers(self, cursor):
        return self.index.covers(cursor)

    def get_thing_at(self, cursor):
        return self.index.get_thing_at(cursor)


class SliceExpr:
    def __init__(self, lower, upper, step):
        self.lower = lower
        self.upper = upper
        self.step = step
        self.start = start(first([lower, upper, step]))
        self.end = end(first([step, upper, lower]))

    def covers(self, cursor):
        return self.lower.covers(cursor)

    def get_thing_at(self, cursor):
        return self.lower.get_thing_at(cursor)


class PrimaryExprWithSliceSuffix:
    def __init__(self, primary_expr, slice_suffix):
        self.primary_expr = primary_expr
        self.slice_suffix = slice_suffix
        self.start = primary_expr.start
        self.end = slice_suffix.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.primary_expr.covers(cursor):
            return self.primary_expr.get_thing_at(cursor)
        return self.slice_suffix.get_thing_at(cursor)


class LoadStmt:
    def __init__(self, arguments):
        assert arguments
        self.arguments = arguments
        self.start = arguments.start
        self.end = arguments.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self.arguments.get_thing_at(cursor)


class Arguments:
    def __init__(self, arguments):
        self.arguments = arguments
        self.start = start(first(arguments))
        self.end = end(first(arguments[::-1]))

    def __len__(self):
        return len(self.arguments)

    def covers(self, cursor):
        if not self.arguments:
            return False
        return self.arguments[0].start <= cursor and cursor < self.arguments[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for argument in self.arguments:
            if argument.covers(cursor):
                return argument.get_thing_at(cursor)


class VarArgExpansion:
    def __init__(self, expr):
        self.expr = expr
        self.start = expr.start
        self.end = expr.end

    def covers(self, cursor):
        return self.expr.covers(cursor)

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self.expr.get_thing_at(cursor)


class KwArgExpansion:
    def __init__(self, expr):
        self.expr = expr
        self.start = expr.start
        self.end = expr.end

    def covers(self, cursor):
        return self.expr.covers(cursor)

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self.expr.get_thing_at(cursor)


class NamedArgument:
    def __init__(self, identifier, value):
        self.identifier = identifier
        self.value = value
        self.start = value.start
        self.end = value.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self.value.get_thing_at(cursor)


class PrimaryExpr:
    def __init__(self):
        raise Exception("Not Implemented Yet")


class UnaryExpr:
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand
        self.start = operand.start
        self.end = operand.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        return self.operand.get_thing_at(cursor)


class BinaryExpr:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
        self.start = left.start
        self.end = right.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.left.covers(cursor):
            return self.left.get_thing_at(cursor)
        assert self.right.covers(cursor)
        return self.right.get_thing_at(cursor)


class Identifier:
    def __init__(self, identifier, start, reference):
        self._identifier = identifier
        self.start = start
        self.end = self.start + len(identifier)
        self._reference = reference

    def identifier(self):
        return self._identifier

    def reference(self):
        return self._reference

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end


class Int:
    def __init__(self, n):
        self.n = n
        self.start = None
        self.end = None


class String:
    def __init__(self, string, start, reference):
        self.string = string
        self.start = start
        self.end = self.start + len(self.string)  # + 2, I guess?
        self.reference = reference

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end


class ListExpr:
    def __init__(self, elements):
        self.elements = elements
        self.start = start(first(elements))
        self.end = end(first(elements[::-1]))

    def __len__(self):
        return len(self.elements)

    def covers(self, cursor):
        if not self.elements:
            return False
        return self.elements[0].start <= cursor and cursor < self.elements[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for entry in self.elements:
            if entry.covers(cursor):
                return entry.get_thing_at(cursor)


class ForClause:
    def __init__(self, target, iterable):
        self.target = target
        self.iterable = iterable
        self.start = target.start
        self.end = iterable.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        if self.target.covers(cursor):
            return self.target.get_thing_at(cursor)
        assert self.iterable.covers(cursor)
        return self.iterable.get_thing_at(cursor)


class IfClause:
    def __init__(self, expr):
        self.expr = expr
        self.start = expr.start
        self.end = expr.end

    def covers(self, cursor):
        return self.expr.covers(cursor)

    def get_thing_at(self, cursor):
        return self.expr.get_thing_at(cursor)


class CompClauses:
    def __init__(self, clauses):
        self.clauses = clauses
        self.start = start(first(clauses))
        self.end = end(first(clauses[::-1]))

    def __len__(self):
        return len(self.clauses)

    def covers(self, cursor):
        if not self.clauses:
            return False
        return self.clauses[0].start <= cursor and cursor < self.clauses[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for clause in self.clauses:
            if clause.covers(cursor):
                return clause.get_thing_at(cursor)


class ListComp:
    def __init__(self, body, clauses):
        self.body = body
        self.clauses = clauses
        self.start = body.start
        self.end = clauses.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.body.covers(cursor):
            return self.body.get_thing_at(cursor)
        assert self.clauses.covers(cursor)
        return self.clauses.get_thing_at(cursor)


class DictEntry:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.start = key.start
        self.end = value.end

    def covers(self, cursor):
        return self.start <= cursor and cursor < self.end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        if self.key.covers(cursor):
            return self.key.get_thing_at(cursor)
        assert self.value.covers(cursor)
        return self.value.get_thing_at(cursor)


class DictExpr:
    def __init__(self, entries):
        self.entries = entries
        self.start = start(first(entries))
        self.end = end(first(entries[::-1]))

    def __len__(self):
        return len(self.entries)

    def covers(self, cursor):
        if not self.entries:
            return False
        return self.entries[0].start <= cursor and cursor < self.entries[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for entry in self.entries:
            if entry.covers(cursor):
                return entry.get_thing_at(cursor)


class DictComp:
    def __init__(self):
        raise Exception("Not Implemented Yet")


class TupleExpr:
    def __init__(self, elements):
        self.elements = elements
        self.start = start(first(elements))
        self.end = end(first(elements[::-1]))

    def __len__(self):
        return len(self.elements)

    def covers(self, cursor):
        if not self.elements:
            return False
        return self.elements[0].start <= cursor and cursor < self.elements[-1].end

    def get_thing_at(self, cursor):
        assert self.covers(cursor)
        for entry in self.elements:
            if entry.covers(cursor):
                return entry.get_thing_at(cursor)


def create_scope_from_parameters(environment, parameters):
    assert isinstance(parameters, Parameters)
    scope = copy(environment)
    for parameter in parameters.parameters:
        scope.bindings[parameter.identifier()] = parameter
    return scope


def parse_parameter(parameter, environment):
    assert isinstance(parameter, ast.arg)
    cursor = Cursor(parameter.lineno, parameter.col_offset)
    return Identifier(parameter.arg, cursor, Reference(environment.label, cursor))


def parse_parameters(parameters, environment):
    assert isinstance(parameters, ast.arguments)

    # bazel does not support kwonlyargs
    assert not parameters.kwonlyargs
    assert not parameters.kw_defaults

    n = len(parameters.args) - len(parameters.defaults)
    parms = [
        parse_parameter(parameter, environment) for parameter in parameters.args[:n]
    ]
    parameters_with_defaults = [
        ParameterWithDefault(
            parse_parameter(parameter, environment), parse_test(default, environment)
        )
        for parameter, default in zip(parameters.args[n:], parameters.defaults)
    ]
    varparameter = (
        [VarParameter(parse_parameter(parameters.vararg, environment))]
        if parameters.vararg
        else []
    )
    kwparameter = (
        [KwParameter(parse_parameter(parameters.kwarg, environment))]
        if parameters.kwarg
        else []
    )
    result = Parameters(parms + parameters_with_defaults + varparameter + kwparameter)
    return create_scope_from_parameters(environment, result), result


def parse_suite(stmts, environment):
    return Suite([parse_stmt(stmt, environment) for stmt in stmts])


def parse_def_stmt(stmt, environment):
    assert isinstance(stmt, ast.FunctionDef)
    scope, parameters = parse_parameters(stmt.args, environment)
    result = DefStmt(stmt.name, parameters, parse_suite(stmt.body, scope))
    environment.bindings[stmt.name] = result
    return result


def parse_identifier(expr, environment):
    # FIXME: The spec says that a load should reference a binding in the same scope if it exists, even if it occurs after the load and a global with the same name exists..
    #        We currently reference the global instead ...
    assert isinstance(expr, ast.expr)
    if isinstance(expr, ast.NameConstant):
        return Identifier(
            str(expr.value),
            Cursor(expr.lineno, expr.col_offset),
            environment.bindings[expr.value],
        )
    assert isinstance(expr, ast.Name)
    cursor = Cursor(expr.lineno, expr.col_offset)
    if isinstance(expr.ctx, ast.Store) and not expr.id in environment.bindings:
        ref = Reference(environment.label, cursor)
        result = Identifier(expr.id, cursor, ref)
        environment.bindings[expr.id] = result
        return result
    else:
        return Identifier(expr.id, cursor, environment.bindings[expr.id])


def parse_string(expr, environment):
    assert isinstance(expr, ast.Str)
    complete_label = copy(environment.label)
    complete_label.target = expr.s
    return String(
        expr.s,
        Cursor(expr.lineno, expr.col_offset),
        environment.targets[str(complete_label)],
    )


def parse_list_expr(expr, environment):
    assert isinstance(expr, ast.List)
    return ListExpr([parse_test(element, environment) for element in expr.elts])


def parse_list_comp(expr, environment):
    assert isinstance(expr, ast.ListComp)
    scope = copy(environment)

    def chain_clauses():
        for generator in expr.generators:
            iterable = parse_test(generator.iter, scope)
            target = parse_primary_expr(generator.target, scope)
            yield ForClause(target, iterable)
            for if_clause in generator.ifs:
                yield IfClause(parse_test(if_clause, scope))

    # must happen before we call parse_test in the ListComp constructor to ensure that scope has been updated
    comp_clauses = CompClauses(list(chain_clauses()))
    return ListComp(parse_test(expr.elt, scope), comp_clauses)


def parse_multi_component_expr(expr, environment):
    assert isinstance(expr, ast.Tuple)
    return TupleExpr([parse_test(element, environment) for element in expr.elts])


def parse_int(num, environment):
    return Int(num)


def parse_dict_expr(expr, environment):
    assert isinstance(expr, ast.Dict)
    return DictExpr(
        [
            DictEntry(parse_test(key, environment), parse_test(value, environment))
            for key, value in zip(expr.keys, expr.values)
        ]
    )


def parse_operand(expr, environment):
    assert isinstance(expr, ast.expr)
    if isinstance(expr, ast.Num):
        return parse_int(expr.n, environment)
    if isinstance(expr, ast.Str):
        return parse_string(expr, environment)
    if isinstance(expr, ast.List):
        return parse_list_expr(expr, environment)
    if isinstance(expr, ast.Dict):
        return parse_dict_expr(expr, environment)
    if isinstance(expr, ast.ListComp):
        return parse_list_comp(expr, environment)
    if isinstance(expr, ast.DictComp):
        return parse_dict_comp(expr, environment)
    if isinstance(expr, ast.Tuple):
        return parse_multi_component_expr(expr, environment)
    return parse_identifier(expr, environment)


def parse_argument(arg, environment):
    assert isinstance(arg, ast.expr)
    if isinstance(arg, ast.Starred):
        return VarArgExpansion(parse_test(arg.value, environment))
    return parse_test(arg, environment)


def parse_keyword(keyword, environment):
    assert isinstance(keyword, ast.keyword)
    if keyword.arg is None:
        return KwArgExpansion(parse_test(keyword.value, environment))
    return NamedArgument(keyword.arg, parse_test(keyword.value, environment))


def parse_arguments(args, keywords, environment):
    return Arguments(
        [parse_argument(arg, environment) for arg in args]
        + [parse_keyword(keyword, environment) for keyword in keywords]
    )


def parse_primary_expr_with_call_suffix(expr, environment):
    assert isinstance(expr, ast.Call)
    return PrimaryExprWithCallSuffix(
        parse_expression(expr.func, environment),
        parse_arguments(expr.args, expr.keywords, environment),
    )


def parse_primary_expr_with_dot_suffix(expr, environment):
    assert isinstance(expr, ast.Attribute)
    return PrimaryExprWithDotSuffix(
        parse_expression(expr.value, environment), expr.attr
    )


def parse_slice_suffix(slice_suffix, environment):
    if isinstance(slice_suffix, ast.Slice):
        lower = (
            parse_expression(slice_suffix.lower, environment)
            if slice_suffix.lower
            else None
        )
        upper = (
            parse_expression(slice_suffix.upper, environment)
            if slice_suffix.upper
            else None
        )
        step = (
            parse_expression(slice_suffix.step, environment)
            if slice_suffix.step
            else None
        )
        return SliceExpr(lower, upper, step)
    assert isinstance(slice_suffix, ast.Index)
    return IndexExpr(parse_expression(slice_suffix.value, environment))


def parse_primary_expr_with_slice_suffix(expr, environment):
    assert isinstance(expr, ast.Subscript)
    return PrimaryExprWithSliceSuffix(
        parse_expression(expr.value, environment),
        parse_slice_suffix(expr.slice, environment),
    )


def parse_primary_expr(expr, environment):
    assert isinstance(expr, ast.expr)
    if isinstance(expr, ast.Call):
        return parse_primary_expr_with_call_suffix(expr, environment)
    if isinstance(expr, ast.Attribute):
        return parse_primary_expr_with_dot_suffix(expr, environment)
    if isinstance(expr, ast.Subscript):
        return parse_primary_expr_with_slice_suffix(expr, environment)
    return parse_operand(expr, environment)


def parse_binary_expr(expr, environment):
    if isinstance(expr, ast.BinOp):
        # TODO: translate op
        return BinaryExpr(
            parse_test(expr.left, environment),
            expr.op,
            parse_test(expr.right, environment),
        )
    if isinstance(expr, ast.BoolOp):
        acc = parse_test(expr.values[-1], environment)
        for value in expr.values[-2::-1]:
            acc = BinaryExpr(parse_expression(value, environment), expr.op, acc)
        return acc
    assert isinstance(expr, ast.Compare)
    acc = parse_test(expr.left, environment)
    for op, comparator in zip(expr.ops, expr.comparators):
        acc = BinaryExpr(acc, op, parse_expression(comparator, environment))
    return acc


def parse_if_expr(expr, environment):
    assert isinstance(expr, ast.IfExp)
    return IfExpr(
        test=parse_test(expr.test, environment),
        body=parse_test(expr.body, environment),
        orelse=parse_test(expr.orelse, environment),
    )


def parse_unary_expr(expr, environment):
    assert isinstance(expr, ast.UnaryOp)
    return UnaryExpr(expr.op, parse_test(expr.operand, environment))


def parse_test(expr, environment):
    assert isinstance(expr, ast.expr)
    if isinstance(expr, ast.IfExp):
        return parse_if_expr(expr, environment)
    if isinstance(expr, ast.UnaryOp):
        return parse_unary_expr(expr, environment)
    if (
        isinstance(expr, ast.BinOp)
        or isinstance(expr, ast.BoolOp)
        or isinstance(expr, ast.Compare)
    ):
        return parse_binary_expr(expr, environment)
    return parse_primary_expr(expr, environment)


def parse_expression(expr, environment):
    # ast merges "Test {',' Test}" into the surrounding List, Tuple or Slice, so here we only have to deal with a single "Test"
    assert isinstance(expr, ast.expr)
    return parse_test(expr, environment)


def parse_load_argument(arg, environment, extension_environment):
    assert isinstance(arg, ast.Str)
    environment.bindings[arg.s] = extension_environment.bindings[arg.s]
    # can't use parse_string because there the strings may be targets, while here they are name bindings
    return String(
        arg.s, Cursor(arg.lineno, arg.col_offset), environment.bindings[arg.s]
    )


def parse_load_keyword(keyword, environment, extension_environment):
    assert isinstance(keyword, ast.keyword)
    assert keyword.arg
    assert isinstance(keyword.value, ast.Str)
    cursor = Cursor(keyword.value.lineno, keyword.value.col_offset)
    return NamedArgument(keyword.arg, String(keyword.value.s, cursor, environment.bindings[keyword.value.s]))


def parse_load_arguments(args, keywords, environment):
    assert args
    assert isinstance(args[0], ast.Str)

    extension_label = parse_label(args[0].s, environment.label)
    path = resolve_label(extension_label, environment.workspace_root)
    _, extension_environment = parse_module(
        ast.parse(open(path).read()), extension_label, environment.workspace_root
    )

    return Arguments(
        [
            parse_load_argument(arg, environment, extension_environment)
            for arg in args[1:]
        ]
        + [
            parse_load_keyword(keyword, environment, extension_environment)
            for keyword in keywords
        ]
    )


def is_load_stmt(stmt):
    if not isinstance(stmt, ast.Expr):
        # print(f"{ast.dump(stmt)} is not a load stmt: not an Expr")
        return False
    expr = stmt.value
    if not isinstance(expr, ast.Call):
        # print(f"{ast.dump(stmt)} is not a load stmt: value is not a Call")
        return False
    func = expr.func
    if not isinstance(func, ast.Name):
        # print(f"{ast.dump(stmt)} is not a load stmt: Called function value is not an identifier")
        return False
    name = func.id
    if name != "load":
        # print(f"{ast.dump(stmt)} is not a load stmt: Called function value identifier is not 'load'")
        return False
    return True


def parse_load_stmt(stmt, environment):
    assert is_load_stmt(stmt)
    call = stmt.value
    return LoadStmt(parse_load_arguments(call.args, call.keywords, environment))


def parse_return_stmt(stmt, environment):
    assert isinstance(stmt, ast.Return)
    return ReturnStmt(parse_expression(stmt.value, environment) if stmt.value else None)


def parse_assignment(stmt, environment):
    # We modify the environment in parse_identifier, not here: The target of
    # the assignment can be an arbitrarily nested expression and we would have
    # to find all identifiers that don't have slice or dot suffixes. Instead we
    # can just check the ctx attribute (Load/Store) of the identifier in
    # parse_identifier.
    if isinstance(stmt, ast.Assign):
        # starlark does not allow x = y = z assignment chains
        assert len(stmt.targets) == 1
        return AssignStmt(
            parse_expression(stmt.targets[0], environment),
            parse_expression(stmt.value, environment),
        )
    assert isinstance(stmt, ast.AugAssign)
    return AssignStmt(
        parse_expression(stmt.target, environment),
        parse_expression(stmt.value, environment),
        stmt.op,
    )


def parse_small_stmt(stmt, environment):
    assert isinstance(stmt, ast.stmt)
    if isinstance(stmt, ast.Return):
        return parse_return_stmt(stmt, environment)
    if isinstance(stmt, ast.Break):
        return BreakStmt()
    if isinstance(stmt, ast.Continue):
        return ContinueStmt()
    if isinstance(stmt, ast.Pass):
        return PassStmt()
    if isinstance(stmt, ast.Assign) or isinstance(stmt, ast.AugAssign):
        return parse_assignment(stmt, environment)
    if is_load_stmt(stmt):
        return parse_load_stmt(stmt, environment)
    assert isinstance(stmt, ast.Expr)
    return parse_expression(stmt.value, environment)


def parse_simple_stmt(stmt, environment):
    # ast merges "SmallStmt {';' SmallStmt} [';']" into the surrounding stmt*, so there is no "SimpleStmt"
    return parse_small_stmt(stmt, environment)


def parse_if_stmt(stmt, environment):
    assert isinstance(stmt, ast.If)
    return IfStmt(
        test=parse_test(stmt.test, environment),
        body=parse_suite(stmt.body, environment),
        orelse=parse_suite(stmt.orelse, environment),
    )


def parse_for_stmt(stmt, environment):
    assert isinstance(stmt, ast.For)
    return ForStmt(
        target=parse_primary_expr(stmt.target, environment),
        iterable=parse_expression(stmt.iter, environment),
        body=parse_suite(stmt.body, environment),
    )


def parse_stmt(stmt, environment):
    assert isinstance(stmt, ast.stmt)
    if isinstance(stmt, ast.FunctionDef):
        return parse_def_stmt(stmt, environment)
    if isinstance(stmt, ast.If):
        return parse_if_stmt(stmt, environment)
    if isinstance(stmt, ast.For):
        return parse_for_stmt(stmt, environment)
    return parse_simple_stmt(stmt, environment)


def parse_module(module, label, workspace_root):
    assert isinstance(module, ast.Module)

    universe = Bindings(
        {
            True: "keyword",
            False: "keyword",
            None: "keyword",
            "cc_library": "builtin",
            "cc_binary": "builtin",
            "cc_test": "builtin",
            "cc_common": "builtin",
            "fail": "builtin",
            "hasattr": "builtin",
            "struct": "builtin",
            "provider": "builtin",
            "any": "builtin",
            "dir": "builtin",
            "CcInfo": "builtin",
            "len": "builtin",
            "str": "builtin",
            "apple_common": "builtin",
            "OutputGroupInfo": "builtin",
            "depset": "builtin",
            "aspect": "builtin",
            "attr": "builtin",
            "Label": "builtin",
            "print": "builtin",
            "rule": "builtin",
        }
    )

    builtin_targets = Targets(
        {
            "//visibility:public": "builtin",
            "//visibility:private": "builtin",
        }
    )

    environment = Environment(
        label, workspace_root, targets=builtin_targets, bindings=universe
    )

    return (
        File(stmts=[parse_stmt(stmt, environment) for stmt in module.body]),
        environment,
    )
