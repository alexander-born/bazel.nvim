from copy import copy
import ast
import os
from label import parse_label, resolve_label, resolve_label_str, resolve_filename
from workspace import find_workspace_root


def parse_module_text(s):
    return ast.parse(s)


def parse_file(f):
    return parse_module_text(f.read())


def parse_file_by_name(fname):
    return parse_file(open(fname))


def collect_imported_symbols(fname, workspace_root=None):
    if workspace_root is None:
        workspace_root = find_workspace_root(fname)
    module = parse_file_by_name(fname)
    for stmt in module.body:
        if not isinstance(stmt, ast.Expr):
            continue
        if not isinstance(stmt.value, ast.Call):
            # print(f"Ignoring {ast.dump(stmt)}: Not a call expression")
            continue
        if not isinstance(stmt.value.func, ast.Name):
            # print(f"Ignoring {ast.dump(stmt)}: Called function is not a 'Name'")
            continue
        if not stmt.value.func.id == "load":
            # print(f"Ignoring {ast.dump(stmt)}: Called function is not 'load'")
            continue

        if not isinstance(stmt.value.args[0], ast.Str):
            # print(f"Ignoring {ast.dump(stmt)}: Arguments must be of type Str")
            continue

        extension_label = stmt.value.args[0].s
        path = resolve_label_str(
            extension_label, resolve_filename(fname, workspace_root), workspace_root
        )
        targets = list(collect_targets(parse_file_by_name(path)))

        for symbol in stmt.value.args[1:]:
            if not isinstance(symbol, ast.Str):
                # print(f"Ignoring {ast.dump(stmt)}: Arguments must be of type Str")
                continue
            name = symbol.s
            matching_targets = [lineno for lineno, n in targets if n == name]
            if not matching_targets:
                raise Exception(f"{name} not found in {path}")
            if len(matching_targets) > 1:
                raise Exception(
                    f"multiple definitions of {name} found in {path}: {matching_targets}"
                )
            lineno = matching_targets[0]
            # print(f"{path}:{lineno}: {name}")
            yield (path, lineno, name, name)

        for kw in stmt.value.keywords:
            if not isinstance(kw.value, ast.Str):
                # print(f"Ignoring {ast.dump(stmt)}: Keyword values must be of type Str")
                continue
            alias = kw.arg
            name = kw.value.s
            matching_targets = [lineno for lineno, n in targets if n == name]
            if not matching_targets:
                raise Exception(f"{name} not found in {path}")
            if len(matching_targets) > 1:
                raise Exception(
                    f"multiple definitions of {name} found in {path}: {matching_targets}"
                )
            lineno = matching_targets[0]
            # print(f"{path}:{lineno}: {alias} = {name}")
            yield (path, lineno, alias, name)


def collect_targets(module):
    assert isinstance(module, ast.Module)
    for stmt in module.body:
        if isinstance(stmt, ast.Expr):
            if not isinstance(stmt.value, ast.Call):
                # print(f"Ignoring {ast.dump(stmt)}: Not a call expression")
                continue
            if not isinstance(stmt.value.func, ast.Name):
                # print(f"Ignoring {ast.dump(stmt)}: Called function is not a 'Name'")
                continue

            name_keywords = [kw for kw in stmt.value.keywords if kw.arg == "name"]

            if len(name_keywords) != 1:
                # print(f"Ignoring {ast.dump(stmt)}: There must be exactly one 'name' keyword per rule")
                continue

            name_keyword = name_keywords[0]
            if not isinstance(name_keyword.value, ast.Str):
                # print(f"Ignoring {ast.dump(stmt)}: Value of keyword 'name' must be a Str")
                continue

            rule = stmt.value.func.id
            name = name_keyword.value.s
            lineno = stmt.lineno
            col_offset = stmt.col_offset
            # print(f"{lineno}:{col_offset}: {rule} {name}")
            yield (lineno, name)
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if not isinstance(target, ast.Name):
                    # print(f"Ignoring {ast.dump(target)}: Target of assignment is not a 'Name'")
                    continue
                name = target.id
                lineno = target.lineno
                col_offset = target.col_offset
                # print(f"{lineno}:{col_offset}: {name}")
                yield (lineno, name)

        elif isinstance(stmt, ast.FunctionDef):
            name = stmt.name
            lineno = stmt.lineno
            col_offset = stmt.col_offset
            # print(f"{lineno}:{col_offset}: def {name}")
            yield (lineno, name)
        # else:
        #    print(f"Ignoring {ast.dump(stmt)}: Don't know how to handle {type(stmt)}")


def find_symbol(symbol, fname, workspace_root=None):
    if workspace_root is None:
        workspace_root = find_workspace_root(fname)

    for path, lineno, alias, name in collect_imported_symbols(fname, workspace_root):
        if alias == symbol:
            # print(f"{path}:{lineno}: {name}")
            return path, lineno


def find_definition(label_str, fname, workspace_root=None):
    # print(f"find_definition({label_str}, {fname}, {workspace_root})")
    if workspace_root is None:
        workspace_root = find_workspace_root(fname)
    label = parse_label(label_str, resolve_filename(fname, workspace_root))
    # print(f"label: {label}")

    build_label = copy(label)
    build_label.target = "BUILD"
    build_fname = resolve_label(build_label, workspace_root)
    # print(f"build_fname: {build_fname}")

    for lineno, name in collect_targets(parse_file_by_name(build_fname)):
        if name == label.target:
            # print(f"{build_fname}:{lineno}: {label.target}")
            return build_fname, lineno


def find_node(root, row, col):
    """
    Returns the last visited node that has a lineno of row and a col_offset less than or equal to col, or None if none was found.
    """

    class Visitor(ast.NodeVisitor):
        def __init__(self, row, col):
            self.row = row
            self.col = col
            self.result = None

        def visit_Str(self, node):
            if node.lineno == self.row and node.col_offset <= self.col:
                self.result = node
            self.generic_visit(node)

        def visit_Name(self, node):
            if node.lineno == self.row and node.col_offset <= self.col:
                self.result = node
            self.generic_visit(node)

    visitor = Visitor(row, col)
    visitor.visit(root)
    return visitor.result


def find_definition_at(fname, text, row, col, workspace_root=None):
    if workspace_root is None:
        workspace_root = find_workspace_root(os.getcwd())
    module = parse_module_text(text)
    node = find_node(module, row, col)
    if isinstance(node, ast.Str):
        return find_definition(node.s, fname, workspace_root)
    elif isinstance(node, ast.Name):
        return find_symbol(node.id, fname, workspace_root)
    else:
        # print(f"Don't know how to go to {type(node)}")
        return None


def get_target_label(fname, text, row, col, workspace_root=None):
    if workspace_root is None:
        workspace_root = find_workspace_root(os.getcwd())
    module = parse_module_text(text)
    node = find_node(module, row, col)
    if isinstance(node, ast.Str):
        return str(parse_label(node.s, resolve_filename(fname, workspace_root)))
    else:
        return None


def print_label(fname, text, row, col, workspace_root=None):
    label = get_target_label(fname, text, row, col, workspace_root)
    if label:
        print(label)
    else:
        print("No label found under cursor.")


def find_definition_in(fname, row, col, workspace_root=None):
    if workspace_root is None:
        workspace_root = find_workspace_root(os.getcwd())
    find_definition_at(fname, open(fname).read(), row, col, workspace_root)
