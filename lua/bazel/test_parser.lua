local M = {}

function M.get_treesitter_query(bufnr, query, capture, opts)
	opts = opts or {}
	local node_at_cursor = vim.treesitter.get_node()

	local tree = vim.treesitter.get_parser(bufnr):parse()[1]
	for id, node, metadata in query:iter_captures(tree:root(), bufnr) do
		if query.captures[id] == capture then
			if node:child_with_descendant(node_at_cursor) ~= nil or node == node_at_cursor then
				return node
			end
		end
	end
	if not opts.optional then
		error("Cursor not in a test")
	end
end

function M.get_text_of_capture(bufnr, query, capture, root)
	for id, node, metadata in query:iter_captures(root, bufnr) do
		if query.captures[id] == capture then
			return vim.treesitter.get_node_text(node, 0)
		end
	end
end

return M
