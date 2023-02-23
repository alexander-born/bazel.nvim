from copy import copy
import os.path
from workspace import get_external_directory, find_package_root

# TODO: bazel defines that labels starting with "@//" always refer to the main repository, even when encountered in a rule used from another repository
# TODO: I'm confused about how '//...' is resolved in other repositories than main:
#       I think that in most contexts it refers to the current repository, but functions (macros) aren't evaluated in the current file and therefore
#       refer to the repository where the macro is called ...
#
#       So ... for "GoToDefinition" in macro code in other repos ... the proper solution would be to offer "macro expansion" so that the user can
#       "GoToDefinition" in the expanded code. And I should not offer "GoToDefinition" in macros because I don't know what the labels will refer to
#       in the final context.
#       Given these constraints, '//...' should refer to the current repository.
#
#       In starlark.py this is not an issue because I only build the ast which doesn't try to resolve any and all strings as other targets. They are
#       just that: strings.


class Label:
    def __init__(self, repository="", package="", target=""):
        assert repository or package or target
        self.repository = repository
        self.package = package
        self.target = target

    def __str__(self):
        return f"@{self.repository}//{self.package}:{self.target}"

    def __repr__(self):
        return f"Label(repository={self.repository}, package={self.package}, target={self.target})"

    def __eq__(self, other):
        return (
            self.repository == other.repository
            and self.package == other.package
            and self.target == other.target
        )


def parse_target(text):
    # returns non-empty target
    assert text.startswith(":") and len(text) > 1
    return text[1:]


def parse_package(text):
    assert text.startswith("//") and len(text) > 2
    colon_index = text.find(":")
    if colon_index == -1:
        # returns non-empty package
        return Label(package=text[2:])
    return Label(package=text[2:colon_index], target=parse_target(text[colon_index:]))


def parse_repository(text):
    assert text.startswith("@") and len(text) > 1
    slash_index = text.find("//")
    if slash_index == -1:
        # returns non-empty repository
        return Label(repository=text[1:])
    # returns non-empty package or target
    label = parse_package(text[slash_index:])
    label.repository = text[1:slash_index]
    return label


def canonicalize(label):
    assert label.repository or label.package or label.target
    if not label.target:
        if label.package:
            label.target = os.path.basename(label.package)
        elif label.repository:
            label.target = label.repository
    return label


def parse_label(text, location):
    """
    This function ignores lexical errors in repository, package and target. It only splits 'text' based on occurences of @, // and :
    location: Label referring to the file we read the label in.
    """
    assert text, "label must not be empty"
    if text.startswith("@"):
        label = parse_repository(text)
    elif text.startswith("//"):
        label = parse_package(text)
        label.repository = location.repository
    elif text.startswith(":"):
        label = copy(location)
        label.target = parse_target(text)
    else:
        label = copy(location)
        label.target = text

    # At this point we have at least one of repository, package or target:
    # parse_repository, parse_package and parse_target each make sure that at least one label part is non-empty (see comments there).
    # If on the other hand the else-branch is taken, we know that text and thus target is non-empty
    assert label.repository or label.package or label.target

    return canonicalize(label)


assert parse_label("@myrepo//my/app/main:app_binary", Label(target="BUILD")) == Label(
    repository="myrepo", package="my/app/main", target="app_binary"
)
assert parse_label("//my/app/main:app_binary", Label(target="BUILD")) == Label(
    repository="", package="my/app/main", target="app_binary"
)
assert parse_label("//my/app", Label(target="BUILD")) == Label(
    repository="", package="my/app", target="app"
)
assert parse_label("//my/app:app", Label(target="BUILD")) == Label(
    repository="", package="my/app", target="app"
)
assert parse_label(
    "//my/app:app", Label(repository="baz", package="foo/bar", target="BUILD")
) == Label(repository="baz", package="my/app", target="app")
assert parse_label(":app", Label(target="BUILD")) == Label(
    repository="", package="", target="app"
)
assert parse_label("app", Label(target="BUILD")) == Label(
    repository="", package="", target="app"
)
assert parse_label(
    ":app", Label(repository="baz", package="foo/bar", target="BUILD")
) == Label(repository="baz", package="foo/bar", target="app")
assert parse_label(
    "app", Label(repository="baz", package="foo/bar", target="BUILD")
) == Label(repository="baz", package="foo/bar", target="app")
assert parse_label("generate.cc", Label(target="BUILD")) == Label(
    repository="", package="", target="generate.cc"
)
assert parse_label("//my/app:generate.cc", Label(target="BUILD")) == Label(
    repository="", package="my/app", target="generate.cc"
)
assert parse_label("testdata/input.txt", Label(target="BUILD")) == Label(
    repository="", package="", target="testdata/input.txt"
)
assert parse_label("//foo/bar/wiz", Label(target="BUILD")) == Label(
    repository="", package="foo/bar/wiz", target="wiz"
)


def _resolve_filename(fname, workspace_root, repository=""):
    assert fname.startswith(workspace_root)

    package_root = find_package_root(fname)
    assert package_root.startswith(workspace_root)

    target = os.path.relpath(fname, start=package_root)
    package = os.path.relpath(package_root, start=workspace_root)
    return Label(repository=repository, package=package, target=target)


def resolve_filename(fname, workspace_root):
    if fname.startswith(workspace_root):
        return _resolve_filename(fname, workspace_root)
    externals = get_external_directory(workspace_root)
    if fname.startswith(externals):
        repository = os.path.relpath(fname, start=externals).split("/")[0]
        return _resolve_filename(fname, externals, repository)
    raise Exception(f"{fname} is neither in {workspace_root} nor in {externals}")


def resolve_label(label, workspace_root):
    """
    Returns path to build file given by 'label' relative to 'workspace_root'.
    Assumes that label.target is a file name.
    """

    root = (
        workspace_root
        if not label.repository
        else os.path.join(get_external_directory(workspace_root), label.repository)
    )
    return os.path.join(root, label.package, label.target)


def resolve_label_str(label_str, location, workspace_root):
    return resolve_label(parse_label(label_str, location), workspace_root)
