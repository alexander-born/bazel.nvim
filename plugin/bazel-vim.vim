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
  let pattern = "\\V\\<" . current_file . "\\>"
  exe "edit" findfile("BUILD", ".;")
  call search(pattern, "w", 0, 500)
endfunction

" MyChoice({list} [, {prompt}])
" Lets user choose an item from {list}. Returns the selected item index or -1.
" If {prompt} is omitted the default prompt is used.
function! MyChoice(list, ...)
    let l:prompt = a:0 ? a:1 : "Choose a bazel target:"
    let l:idx = inputlist(insert(map(copy(a:list), '(1 + v:key) . ". " . v:val'), l:prompt))
    if l:idx >= 1 && l:idx <= len(a:list)
        return l:idx - 1
    endif
    return -1
endfunction

" example usage

function! BazelGetCurrentBufTarget()
    let g:current_bazel_target = py3eval("bazel_vim.get_bazel_target()")
    let g:current_bazel_target = split(g:current_bazel_target, "\n")
    if len(g:current_bazel_target) > 1
        let l:choice = MyChoice(g:current_bazel_target)
        let g:current_bazel_target = g:current_bazel_target[l:choice]
    else
        let g:current_bazel_target = g:current_bazel_target[0]
    endif
endfunction

function! RunBazel()
    let l:cwd = py3eval("bazel_vim.get_workspace_root()")
    :new
    :call termopen('bazel ' . g:bazel_command . ' ' . g:current_bazel_target, {'cwd':l:cwd })
endfunction

function! RunBazelHere(command)
    :let g:bazel_command = a:command
    :call BazelGetCurrentBufTarget()
    :call RunBazel()
endfunction

function! PrintLabel()
    python3 bazel_vim.print_label()
endfunction

function! GetLabel()
    return py3eval("bazel_vim.get_target_label()")
endfunction

command! -nargs=0 PrintLabel call PrintLabel()
command! -nargs=0 GetLabel call GetLabel()
