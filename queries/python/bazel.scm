;; Match undecorated functions
((function_definition
    name: (identifier) @test.name)
    (#match? @test.name "^test"))
    @test.definition
;; Match decorated function, including decorators in definition
(decorated_definition
    ((function_definition
    name: (identifier) @test.name)
    (#match? @test.name "^test")))
    @test.definition
;; Match decorated classes, including decorators in definition
(decorated_definition
    (class_definition
    name: (identifier) @namespace.name))
    @namespace.definition
;; Match undecorated classes: namespaces nest so #not-has-parent is used
;; to ensure each namespace is annotated only once
(
    (class_definition
    name: (identifier) @namespace.name)
    @namespace.definition
    (#not-has-parent? @namespace.definition decorated_definition)
)
