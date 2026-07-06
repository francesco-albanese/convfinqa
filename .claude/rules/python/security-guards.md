# Security guard rules

## Tool SQL policy

`sql_query` policy checks must reject broad `cells` scans. A query is scoped only if
it uses literal equality or a finite literal `IN (...)` predicate on `row_label`
and/or `col_label`.

Reject wildcard predicates, `IS NOT NULL`, broad `OR`, literal tautologies,
column self-equality, constant `IN`, subqueries, comments, semicolon chains,
unknown tables, and non-`cells` identifiers before execution.

Blocked tool calls must not expose raw tool names or raw arguments through
streams, message parts, LLM replay wire messages, observability span names, or
observability inputs. Persist only a sanitized blocked marker and non-sensitive
reason.

## Output guard persistence

If output guarding blocks after any assistant text has already streamed, persisted
assistant `content` and text parts must be replaced with the fixed refusal only.
Never persist `safe prefix + refusal` after a guard block.

Guard reasoning deltas with the same leakage rules before streaming or
persistence. If reasoning trips the guard, do not emit or persist the unsafe
reasoning text; surface only the fixed refusal as assistant text.

## Eval answer matching

The answer-matching evaluator scores the final answer figure in a model answer,
not intermediate numbers in explanatory prose. If the answer figure appears
before a parenthetical calculation note, score that answer-bearing prefix rather
than the trailing calculation numbers. This preserves conversational answers such
as `Revenue moved from 100 to 118, so 18%.` and `The answer is 18% (computed from
118 - 100).`.
