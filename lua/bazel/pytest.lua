local queries = require("nvim-treesitter.query")
local ts_utils = require("nvim-treesitter.ts_utils")

local M = {}

local function get_treesitter_query(bufnr, query, opts)
	local node_at_cursor = ts_utils.get_node_at_cursor()
	local gtests = queries.get_capture_matches(bufnr, query, "bazel")
	for _, m in pairs(gtests) do
		if ts_utils.is_parent(m.node, node_at_cursor) or m.node == node_at_cursor then
			return m.node
		end
	end
	if not opts.optional then
		error("Cursor not in a test")
	end
end

local function get_text_of_capture(bufnr, query, root)
	local node = queries.get_capture_matches(bufnr, query, "bazel", root)[1].node
	return vim.treesitter.query.get_node_text(node, 0)
end

local function get_test_info()
	local bufnr = vim.fn.bufnr()
	local test_node = get_treesitter_query(bufnr, "@test.definition")
	local namespace_node = get_treesitter_query(bufnr, "@namespace.definition", { optional = true })

	local namespace = nil
	if namespace_node then
		namespace = get_text_of_capture(bufnr, "@namespace.name", namespace_node)
	end
	return {
		namespace = namespace,
		name = get_text_of_capture(bufnr, "@test.name", test_node),
	}
end

function M.get_test_filter()
	local test_info = get_test_info()
	local filter = test_info.name
	if test_info.namespace then
		filter = test_info.namespace .. " and " .. test_info.name
	end
	return '-k="' .. filter .. '"'
end

return M
