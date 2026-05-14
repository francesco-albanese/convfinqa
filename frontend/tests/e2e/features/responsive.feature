Feature: Responsive sidebar drawer

  As a user on a smaller viewport
  I want a hamburger that opens the sidebar as a drawer
  So that the chat surface is not crowded out by navigation

  Scenario: Below 1024px, the hamburger toggles the sidebar drawer
    Given my viewport is 800 by 800
    And I open the empty app
    Then the hamburger button is visible
    And the sidebar drawer is closed
    When I open the sidebar drawer
    Then the sidebar drawer is open
    When I dismiss the sidebar drawer by clicking the backdrop
    Then the sidebar drawer is closed

  Scenario: At 1280px the hamburger is hidden and the sidebar is always visible
    Given my viewport is 1280 by 800
    And I open the empty app
    Then the hamburger button is hidden
    And the sidebar is visible
