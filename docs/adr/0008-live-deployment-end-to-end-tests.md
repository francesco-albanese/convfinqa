# Live deployment end-to-end tests

Date: 30-05-2026

Status: Superseded on 23-08-2026 by the local-only project decision.

The hosted sandbox, AWS authentication, paid-provider smoke test, and deployment
workflow described below are retired historical context. Active CI uses the
deterministic local Playwright browser-integration suite with local PostgreSQL
and FastAPI. It requires no AWS credentials, hosted sandbox, or paid provider.

The test vocabulary must distinguish mocked browser integration tests from live End-to-end tests. Live End-to-end tests prove the deployed sandbox path with real auth, backend, persistence, streaming, and LLM integration; the existing route-intercepted Playwright suite remains valuable, but it must not be treated as proof that the deployed product works.

## Context

The glossary defines an End-to-end test as a test of the live deployed product exactly as a user experiences it: real browser, real deployed app, real auth, real data stores, real LLM integration, real streaming, and real persistence. No mocks, stubs, fakes, or route interception are allowed anywhere in an End-to-end test.

The existing Playwright suite does not meet that definition. It intercepts routes and replaces auth, backend responses, document retrieval, chat streams, and logout with test doubles. That suite is still useful because it exercises browser behavior, frontend state, and UI flows deterministically, but it is a browser integration suite, not a live deployment End-to-end suite.

The deployment gap is operationally important. A route-intercepted suite can pass while Cognito Hosted UI, Lambda auth callbacks, backend JWT validation, Aurora persistence, provider credentials, streaming, or deployed routing are broken. The project therefore needs a small sandbox smoke check that proves the live product path still works, while keeping broader deterministic browser coverage local and cheap.

## Decision

End-to-end tests mean the live product path: real browser, deployed app, auth, data store, LLM/provider call, streaming, and persistence, with no mocks, stubs, fakes, or route interception.

The existing route-intercepted Playwright suite is renamed and documented as browser integration testing. It remains the deterministic suite for frontend behavior and UI state.

The deployed End-to-end suite is intentionally small: one sandbox smoke path that signs in through the normal product auth flow, opens the app, sends a real prompt against a pinned Document, observes the streamed assistant response, verifies Conversation persistence after reload, and deletes the Conversation through product behavior. This bounds LLM and infrastructure cost while proving the systems most likely to fail only after deployment.

Broader no-mock End-to-end coverage runs against the Docker-composed app stack during development. It still avoids route interception and mocks, but the deployment target is local rather than sandbox.

Authentication uses the normal `/sign-in` to `/api/auth/login` to Cognito Hosted UI OAuth flow with a dedicated non-production e2e user. Terraform creates that user, generates its password, and stores the password in SSM SecureString, not Secrets Manager. Production remains Google-only unless explicitly changed.

## Considered and rejected

- Keeping the route-intercepted Playwright suite named as End-to-end was rejected because it conflicts with the glossary and can pass while deployed auth, backend, persistence, streaming, or provider integration is broken.
- A test-only login endpoint was rejected because it bypasses the exact OAuth path this suite exists to prove.
- Automating a Google account was rejected because it is less deterministic in CI than Cognito-native username/password auth and makes non-production tests depend on an external identity workflow.
- Enabling Cognito-native auth in production was rejected because this user exists only to exercise non-production deployments. Production remains Google-only unless a separate product decision changes that boundary.
- Running broad live sandbox coverage was rejected because every prompt may spend LLM/provider and infrastructure budget. The live suite is a smoke check; breadth belongs in browser integration tests and local Docker End-to-end tests.

## Consequences

Existing route-intercepted Playwright tests must be named and documented as browser integration tests. Test names, scripts, CI job names, and docs should reserve End-to-end for no-mock product-system tests.

Live End-to-end runs require `E2E_BASE_URL`, `E2E_EMAIL`, and `E2E_PASSWORD`, and must fail fast when those are absent. The password is read from SSM SecureString for the dedicated non-production e2e user.

The sandbox smoke test must clean up every Conversation it creates through product behavior. Cleanup is part of the integration check because it proves the deployed deletion path, not only the prompt path.

Terraform state is secret-bearing because it contains the generated e2e password. Operators must treat the environmental state backend accordingly.
