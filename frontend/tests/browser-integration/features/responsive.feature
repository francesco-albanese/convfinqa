Feature: Responsive sidebar drawer

  As a user on a smaller viewport
  I want a hamburger that opens the sidebar as a drawer
  So that the chat surface is not crowded out by navigation

  Scenario: 600px viewport — sidebar drawer + bottom sheet
    Given my viewport is 600 by 900
    And a stubbed backend with the JKHY 2009 page-28-3 document seeded
    And I open the app with the JKHY 2009 page-28-3 document pinned
    Then the hamburger button is visible
    And the View document button is visible
    And the sidebar drawer is closed
    And the right panel sheet is closed
    And the layout has no horizontal scrollbar
    When I open the sidebar drawer
    Then the sidebar drawer is open
    When I dismiss the sidebar drawer by clicking the backdrop
    Then the sidebar drawer is closed
    When I click the View document button
    Then the right panel sheet is open
    When I dismiss the right panel sheet via the close button
    Then the right panel sheet is closed
    And the layout has no horizontal scrollbar

  Scenario: 900px viewport — same behavior
    Given my viewport is 900 by 800
    And a stubbed backend with the JKHY 2009 page-28-3 document seeded
    And I open the app with the JKHY 2009 page-28-3 document pinned
    Then the hamburger button is visible
    And the View document button is visible
    And the sidebar drawer is closed
    And the right panel sheet is closed
    When I open the sidebar drawer
    Then the sidebar drawer is open
    When I dismiss the sidebar drawer by clicking the backdrop
    Then the sidebar drawer is closed
    When I click the View document button
    Then the right panel sheet is open
    When I dismiss the right panel sheet via the close button
    Then the right panel sheet is closed

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

  Scenario: Below 1024px with a pinned document, the View document button opens a bottom sheet
    Given my viewport is 600 by 900
    And a stubbed backend with the JKHY 2009 page-28-3 document seeded
    And I open the app with the JKHY 2009 page-28-3 document pinned
    Then the View document button is visible
    And the right panel sheet is closed
    When I click the View document button
    Then the right panel sheet is open
    When I dismiss the right panel sheet via the close button
    Then the right panel sheet is closed

  Scenario: At 1280px with a pinned document, no View document button is shown
    Given my viewport is 1280 by 800
    And a stubbed backend with the JKHY 2009 page-28-3 document seeded
    And I open the app with the JKHY 2009 page-28-3 document pinned
    Then the View document button is hidden

  Scenario: Below lg, Escape closes the sidebar drawer and returns focus to the hamburger
    Given my viewport is 600 by 900
    And I open the empty app
    When I open the sidebar drawer
    Then the sidebar drawer is open
    And the sidebar drawer has role dialog and aria-modal true
    When I press Escape
    Then the sidebar drawer is closed
    And the hamburger button has focus

  Scenario: Below lg, Escape closes the right-panel sheet and returns focus to the trigger
    Given my viewport is 600 by 900
    And a stubbed backend with the JKHY 2009 page-28-3 document seeded
    And I open the app with the JKHY 2009 page-28-3 document pinned
    When I click the View document button
    Then the right panel sheet is open
    And the right panel sheet has role dialog and aria-modal true
    When I press Escape
    Then the right panel sheet is closed
    And the View document button has focus
