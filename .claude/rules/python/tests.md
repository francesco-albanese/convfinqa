- I ABSOLUTELY HATE meaningless tests added only for the sake of increasing the
coverage. I am going to ask you to write in a TDD fashion but silly tests like
for example tests that check if we are able to import modules correctly,
or meaningless tests where we check implementation details MUST be avoided at 
all costs!
- the tests should be written with the user behaviour in mind, always thinking
about how the user would actually use the application for real
- the assertions should be kept to a minimum, only checking the actual logic
and the potential edge cases but WITHOUT EXAGGERATING. Tests should be easy to
read, extra logic for mocking and fixtures and long functions should be 
extracted to a separate file rather than polluting the main test file
- hexagonal architecture should help with mocking, the abstractions will be 
created with the ability to quickly swap a dependency for testing purposes 
without having to do heavy monkey patching. If the implementation is hard-coding
something that could be abstracted away for testing, then do so!