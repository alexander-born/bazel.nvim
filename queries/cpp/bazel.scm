;; "TEST", "TEST_F", "TEST_P", "TYPED_TEST_P", "TYPED_TEST" }
(function_definition
  (function_declarator
    (identifier) @test.type(#match? @test.type "TEST")
    (parameter_list
      (parameter_declaration) @test.suite
      (parameter_declaration) @test.name))) @test.definition
