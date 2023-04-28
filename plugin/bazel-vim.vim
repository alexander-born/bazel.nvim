let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
from os.path import normpath, join
import vim
plugin_root_dir = vim.eval('s:plugin_root_dir')
python_root_dir = normpath(join(plugin_root_dir, '..', 'plugin'))
sys.path.insert(0, python_root_dir)
import bazel_vim
EOF

function! GoToBazelDefinition()
    python3 bazel_vim.find_definition()
endfunction

function! GoToBazelTarget()
  let current_file = expand("%:t")
  exe "edit" py3eval("bazel_vim.get_build_file()")
  let pattern = "\\V\\<" . current_file . "\\>"
  call search(pattern, "w", 0, 500)
endfunction

function! PrintLabel()
    python3 bazel_vim.print_label()
endfunction

function! GetLabel()
    return py3eval("bazel_vim.get_target_label()")
endfunction

command! -nargs=0 PrintLabel call PrintLabel()
command! -nargs=0 GetLabel call GetLabel()
