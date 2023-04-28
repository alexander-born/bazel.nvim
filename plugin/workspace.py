import os.path
import subprocess


def _find_file(fname, markers):
    # not strictly necessary, but helpful for debugging
    assert os.path.exists(fname)

    for marker in markers:
        path = os.path.abspath(fname)
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        while path != "/":
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
