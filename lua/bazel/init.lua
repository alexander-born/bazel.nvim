local M = {}

local function get_parent_path_with_file(path, file)
	local initial_path = path or vim.fn.expand(("#%d:p:h"):format(vim.fn.bufnr()))
	if initial_path == "" then
		return nil
	end
	local workspace = initial_path
	while 1 do
		if vim.fn.filereadable(workspace .. "/" .. file) == 1 then
			break
		end
		if workspace == "/" then
			return nil
		end
		workspace = vim.fn.fnamemodify(workspace, ":h")
	end
	return workspace
end

function M.get_workspace(path)
	return get_parent_path_with_file(path, "WORKSPACE")
end

function M.get_workspace_name(path)
	local workspace_file = M.get_workspace(path) .. "/WORKSPACE"
	local workspace_content = vim.fn.system("cat " .. workspace_file)
	return workspace_content:match('workspace%(name = "(.-)"%)')
end

function M.is_bazel_workspace(path)
	return M.get_workspace(path) ~= nil
end

local function get_cache_file(path)
	return get_parent_path_with_file(path, "DO_NOT_BUILD_HERE") .. "/DO_NOT_BUILD_HERE"
end

function M.is_bazel_cache(path)
	return get_parent_path_with_file(path, "DO_NOT_BUILD_HERE") ~= nil
end

function M.get_workspace_from_cache(path)
	return vim.fn.system("cat " .. get_cache_file(path))
end

local function get_executable(target, workspace)
	local executable = target:gsub(":", "/")
	return workspace .. "/" .. executable:gsub("//", "bazel-bin/")
end

local function call_with_bazel_targets(callback)
	local fname = vim.fn.expand("%:p")
	local workspace = M.get_workspace(fname)
	if workspace == nil then
		print("Not in a bazel workspace.")
		return
	end
	local fname_rel = fname:match(workspace .. "/(.*)")
	local function query_targets(bazel_info)
		vim.pretty_print(bazel_info.stdout)
		local file_label = bazel_info.stdout[1]
		local file_package = file_label:match("(.*):")
		local function query_cmd(attr)
			return "attr(" .. attr .. "," .. file_label .. "," .. file_package .. ":*)"
		end
		M.query("'" .. query_cmd("srcs") .. " union " .. query_cmd("hdrs") .. "'", {
			workspace = bazel_info.workspace,
			on_success = function(bazel_info_)
				callback(bazel_info_.stdout)
			end,
		})
	end
	M.query(fname_rel, { on_success = query_targets, workspace = workspace })
end

function M.call_with_bazel_target(callback)
	local function choice(targets)
		local n = vim.tbl_count(targets)
		if n == 0 then
			print("No bazel targets found for this file.")
			return
		end
		if n == 1 then
			callback(targets[1])
		end
		if n > 1 then
			vim.ui.select(targets, { prompt = "Choose bazel target:" }, function(target)
				if target ~= nil then
					callback(target)
				end
			end)
		end
	end
	call_with_bazel_targets(choice)
end

local function create_window()
	local new_buf = nil
	if
		vim.tbl_count(vim.api.nvim_list_wins()) == 1
		or vim.g.bazel_win == nil
		or not vim.api.nvim_win_is_valid(vim.g.bazel_win)
	then
		vim.cmd("new")
		vim.g.bazel_win = vim.api.nvim_get_current_win()
		new_buf = vim.api.nvim_get_current_buf()
	else
		vim.api.nvim_set_current_win(vim.g.bazel_win)
	end
	vim.api.nvim_win_set_buf(vim.g.bazel_win, vim.api.nvim_create_buf(false, true))
	if new_buf ~= nil then
		vim.api.nvim_buf_delete(new_buf, {})
	end
end

local function close_window()
	vim.api.nvim_win_close(vim.g.bazel_win, true)
end

local function store_for_run_last(command, args, target, workspace, opts)
	vim.g.bazel_last_command = command
	vim.g.bazel_last_args = args
	vim.g.bazel_last_target = target
	vim.g.bazel_last_workspace = workspace
	vim.g.bazel_last_opts = opts
end

local function get_bazel_info(workspace, opts)
	local info = {}
	info.workspace = workspace
	info.workspace_name = M.get_workspace_name(workspace)
	if opts.target then
		info.executable = get_executable(opts.target, workspace)
		info.runfiles = info.executable .. ".runfiles"
	end
	return info
end

local function get_options(command, workspace, opts, bazel_info)
	opts = opts or {}
	local result = {
		cwd = workspace,
		on_exit = function(_, success)
			if success ~= 0 then
				return
			end
			if opts.on_success ~= nil then
				close_window()
				opts.on_success(bazel_info)
			end
		end,
	}
	if command == "cquery" or command == "query" then
		bazel_info.stdout = {}
		result.stdout_buffered = true
		result.on_stdout = function(_, stdout)
			for _, line in pairs(stdout) do
				if line ~= "" then
					line = line:gsub("\r", "")
					table.insert(bazel_info.stdout, line)
				end
			end
		end
	end
	return result
end

function M.run(command, args, target, workspace, opts)
	local bazel_info = get_bazel_info(workspace, { target = target })
	store_for_run_last(command, args, target, workspace, opts)
	create_window()
	vim.fn.termopen(
		"bazel " .. command .. " " .. args .. " " .. target,
		get_options(command, workspace, opts, bazel_info)
	)
	vim.fn.feedkeys("G")
end

function M.run_last()
	if vim.g.bazel_last_command == nil then
		print("Last bazel command not set.")
		return
	end
	M.run(
		vim.g.bazel_last_command,
		vim.g.bazel_last_args,
		vim.g.bazel_last_target,
		vim.g.bazel_last_workspace,
		vim.g.bazel_last_opts
	)
end

-- opts: on_success function(bazel_info) -- bazel_info hast the following fields: workspace, workspace_name, executable, runfiles
function M.run_here(command, args, opts)
	M.call_with_bazel_target(function(target)
		M.run(command, args, target, M.get_workspace(), opts)
	end)
end

-- opts: on_success function(bazel_info) -- bazel_info hast the following fields: workspace, workspace_name, optional(stdout, executable, runfiles)
function M.execute(command, args, opts)
	local workspace = opts.workspace or M.get_workspace()
	create_window()
	vim.fn.termopen(
		"bazel " .. command .. " " .. args,
		get_options(command, workspace, opts, get_bazel_info(workspace, {}))
	)
	vim.fn.feedkeys("G")
end

-- opts: on_success function(bazel_info) -- bazel_info hast the following fields: workspace, workspace_name, stdout
function M.query(args, opts)
	args = args .. " --color no --curses no --noshow_progress"
	M.execute("query", args, opts)
end

-- opts: on_success function(bazel_info) -- bazel_info hast the following fields: workspace, workspace_name, stdout
function M.cquery(args, opts)
	args = args .. " --color no --curses no --noshow_progress"
	M.execute("cquery", args, opts)
end
return M
