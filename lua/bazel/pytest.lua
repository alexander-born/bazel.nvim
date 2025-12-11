local test_parser = require("bazel.test_parser")

local function get_test_info()
	local bufnr = vim.fn.bufnr()
	local query = vim.treesitter.query.get("python", "bazel")
	local test_node = test_parser.get_treesitter_query(bufnr, query, "test.definition")
	local namespace_node = test_parser.get_treesitter_query(bufnr, query, "namespace.definition", { optional = true })

	local namespace = nil
	if namespace_node then
		namespace = test_parser.get_text_of_capture(bufnr, query, "namespace.name", namespace_node)
	end
	return {
		namespace = namespace,
		name = test_parser.get_text_of_capture(bufnr, query, "test.name", test_node),
	}
end

local M = {}

function M.get_test_filter_args()
	local test_info = get_test_info()
	local filter = test_info.name
	if test_info.namespace then
		filter = test_info.namespace .. " and " .. test_info.name
	end
	return { "-k", filter }
end

return M
