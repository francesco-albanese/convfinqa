Feature: Auth session

  As a visitor
  I want to be able to sign out
  So that I can leave the app securely

  Scenario: Sign out clears the session and returns to /sign-in
    Given I am signed in on the app page
    When I open the user menu
    And I select the "Sign out" menu item
    Then I land on the sign-in page
