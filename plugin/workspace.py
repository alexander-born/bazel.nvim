import os.path
import subprocess
import vim


def _find_file(fname, markers):
    # not strictly necessary, but helpful for debugging
    assert os.path.exists(fname)

    path = os.path.abspath(fname)
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    while path != "/":
        for marker in markers:
            candidate = os.path.join(path, marker)
            if os.path.exists(candidate):
                return candidate
        path = os.path.dirname(path)
    raise Exception(f"Could not find {markers} file in any parent directory.")


def find_build_file(fname):
    return _find_file(fname, ["BUILD", "BUILD.bazel"])


def find_package_root(fname):
    return os.path.dirname(find_build_file(fname))


def find_build_name(fname):
    return os.path.basename(find_build_file(fname))


def find_workspace_root(fname):
    return os.path.dirname(_find_file(fname, ["WORKSPACE", "WORKSPACE.bazel"]))


def output_base(workspace_root):
    bazel_cmd = vim.eval("g:bazel_cmd") or "bazel"
    with open(os.devnull, "w") as devnull:
        result = subprocess.check_output(
            [bazel_cmd, "info", "output_base"], cwd=workspace_root, stderr=devnull
        )[:-1].decode("utf-8")
    return result


def get_external_directory(workspace_root):
    return os.path.join(output_base(workspace_root), "external")
