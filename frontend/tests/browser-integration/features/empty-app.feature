Feature: Empty app shell

  As a signed-in user with no pinned document
  I want a clear empty state and a collapsible sidebar that remembers my preference
  So that I know what to do next when I land on /app

  Scenario: New user sees the empty state
    Given I open the empty app
    Then I see the empty-state hero with copy "Pin a document to start chatting"
    And the right panel is closed

  Scenario: Sidebar collapse persists across reload
    Given I open the empty app
    Then the sidebar is expanded
    When I collapse the sidebar
    Then the sidebar is collapsed
    When I reload the page
    Then the sidebar is collapsed
