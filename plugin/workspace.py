import os.path
import subprocess


def _find_parent_directory_containing_file(fname, marker):
    # not strictly necessary, but helpful for debugging
    assert os.path.exists(fname)

    fname = os.path.abspath(fname)

    if not os.path.isdir(fname):
        fname = os.path.dirname(fname)
    while fname != "/":
        if os.path.exists(os.path.join(fname, marker)):
            return fname
        fname = os.path.dirname(fname)
    raise Exception(f"Could not find {marker} file in any parent directory.")


def find_package_root(fname):
    return _find_parent_directory_containing_file(fname, "BUILD")


def find_workspace_root(fname):
    return _find_parent_directory_containing_file(fname, "WORKSPACE")


def output_base(workspace_root):
    with open(os.devnull, "w") as devnull:
        result = subprocess.check_output(
            ["bazel", "info", "output_base"], cwd=workspace_root, stderr=devnull
        )[:-1].decode("utf-8")
    if (
        result
        == "/home/racko/.cache/bazel/_bazel_racko/155a8ac14ffc286331e22db9c5281203"
    ):
        result = "/home/racko/.cache/bazel/_bazel_root/0b502cf25d074c0253821d023c1a4596"
    if (
        result
        == "/home/racko/.cache/bazel/_bazel_racko/0b502cf25d074c0253821d023c1a4596"
    ):
        result = "/home/racko/.cache/bazel/_bazel_root/0b502cf25d074c0253821d023c1a4596"
    return result


def get_external_directory(workspace_root):
    return os.path.join(output_base(workspace_root), "external")
