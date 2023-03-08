local test_parser = require("bazel.test_parser")

local M = {}

local function get_gtest_info()
	local bufnr = vim.fn.bufnr()
	local gtest_node = test_parser.get_treesitter_query(bufnr, "@test.definition")
	return {
		type = test_parser.get_text_of_capture(bufnr, "@test.type", gtest_node),
		suite = test_parser.get_text_of_capture(bufnr, "@test.suite", gtest_node),
		name = test_parser.get_text_of_capture(bufnr, "@test.name", gtest_node),
	}
end

local function get_gtest_filter()
	local test_info = get_gtest_info()
	local test_filter = test_info.suite .. "." .. test_info.name
	if test_info.type == "TEST_P" then
		test_filter = "*" .. test_filter .. "*"
	end
	if test_info.type == "TYPED_TEST" or test_info.type == "TYPED_TEST_P" then
		test_filter = "*" .. test_info.suite .. "*" .. test_info.name
	end
	return test_filter
end

function M.get_gtest_filter_args()
	return { "--gtest_filter=" .. get_gtest_filter() }
end

return M
