Feature: Sign in stub

  As a visitor
  I want to land on /app after clicking either sign-in button
  So that I can start using the product without a real auth flow

  Scenario: Email + password lands on /app
    Given I open the sign-in page
    When I click the "Sign in" button
    Then I land on the app page
    And my dev user id is persisted

  Scenario: Continue with Google lands on /app
    Given I open the sign-in page
    When I click the "Continue with Google" button
    Then I land on the app page
    And my dev user id is persisted
