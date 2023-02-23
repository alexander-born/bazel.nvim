# Features
 - go to definition insides bazel files
 - build/test/run bazel target of current buffer
 - jump to BUILD file of current buffer
 - start debugger of gtest at current cursor position (requires nvim-dap or vimspector)
 - get full bazel label at current cursor position inside BUILD file
 
 For auto completion of bazel targets checkout [cmp-bazel](https://github.com/alexander-born/cmp-bazel)
 
### Installation
Use your favorite package mananger. Example lazy:
```lua
 return {'alexander-born/bazel.nvim', dependencies = {'nvim-treesitter/nvim-treesitter'} },
```

### Configuration
See configuration in todo

### vim functions:
```viml
BazelGetCurrentBufTarget()   " Get the bazel target of current buffer
GoToBazelTarget()            " Jumps to the BUILD file of current target
RunBazelHere(command)        " Runs the current bazel target with given command
RunBazel()                   " Repeats the last bazel run
GetLabel()                   " Returns bazel label of target in build file
```

### lua functions:
```lua
local bazel = require('bazel')
local bazel_gtest = require('bazel.gtest')

bazel.run_last()
bazel.run_here(command, args, opts)
bazel.query(command, args, opts)
bazel.cquery(command, args, opts)

bazel.get_workspace(path)
bazel.get_workspace_name(path)
bazel.is_bazel_workspace(path)
bazel.is_bazel_cache(path)
bazel.get_workspace_from_cache(path)

bazel_gtest.get_gtest_filter()
```
