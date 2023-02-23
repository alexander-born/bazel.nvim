import bazel
import vim
import os.path
import subprocess


def jump_to_location(filename, line):
    filenameEscaped = filename.replace(" ", "\\ ")
    if filename != vim.current.buffer.name:
        command = "edit %s" % filenameEscaped
    else:
        command = "normal! m'"
    try:
        vim.command(command)
    except:
        return
    vim.current.window.cursor = (line, 0)


def find_definition():
    row, col = vim.current.window.cursor
    result = bazel.find_definition_at(
        vim.current.buffer.name, "\n".join(vim.current.buffer), row, col
    )
    if result is None:
        print("Failed to find the definition")
        return
    jump_to_location(*result)


def print_label():
    row, col = vim.current.window.cursor
    bazel.print_label(vim.current.buffer.name, "\n".join(vim.current.buffer), row, col)


def get_target_label():
    row, col = vim.current.window.cursor
    return bazel.get_target_label(
        vim.current.buffer.name, "\n".join(vim.current.buffer), row, col
    )


def bazel_query(args, ws_root):
    command = f"bazel query {args} --color no --curses no --noshow_progress"
    return subprocess.check_output(command.split(" "), cwd = ws_root).decode("utf-8").strip("\n")


def find_label_in(attr, bazel_file_label, bazel_file_package, ws_root):
    return bazel_query(f"""attr('{attr}',{bazel_file_label},{bazel_file_package}:*)""", ws_root)


def get_label(bazel_file_label, bazel_file_package, ws_root):
    label = find_label_in("srcs", bazel_file_label, bazel_file_package, ws_root)
    if not label:
        label = find_label_in("hdrs", bazel_file_label, bazel_file_package, ws_root)
    return label

def get_workspace_root():
    return bazel.find_workspace_root(vim.current.buffer.name)

def get_bazel_target():
    fname = vim.current.buffer.name
    ws_root = bazel.find_workspace_root(fname)
    fname_rel = os.path.relpath(fname, ws_root)
    bazel_file_label = bazel_query(f"{fname_rel}", ws_root)
    bazel_file_package = bazel_file_label.split(":")[0]
    return get_label(bazel_file_label, bazel_file_package, ws_root)
