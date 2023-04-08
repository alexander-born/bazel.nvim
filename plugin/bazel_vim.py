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
