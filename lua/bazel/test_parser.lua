local queries = require("nvim-treesitter.query")
local ts_utils = require("nvim-treesitter.ts_utils")

local M = {}

function M.get_treesitter_query(bufnr, query, opts)
	opts = opts or {}
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

function M.get_text_of_capture(bufnr, query, root)
	local node = queries.get_capture_matches(bufnr, query, "bazel", root)[1].node
	return vim.treesitter.get_node_text(node, 0)
end

return M
