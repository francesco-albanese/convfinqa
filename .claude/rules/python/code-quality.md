- use the zen of python
- clear and concise function, single responsibility
- dependencies should be injected following the hexagonal architecture pattern
prioritising testability
- functions should never be too long (more than 250 lines is unreadable and
hard to maintain)
- if a module requires multiple functions think about extracting it away into
utils, to avoid polluting the main function of each module 