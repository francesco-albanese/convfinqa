Feature: Light/dark theme follows system preference and user override

  As a user
  I want the app to render in my OS color scheme on first load and honour my saved override
  So that the UI matches my preference without flashing or resetting

  Scenario: Default theme matches the system preference
    Given my system prefers light
    And I have not saved a theme preference
    When I open the home page
    Then the document theme is "light"

  Scenario: Saved "light" override survives a reload
    Given my system prefers dark
    And I have saved "light" as my theme
    When I open the home page
    Then the document theme is "light"
    When I reload the page
    Then the document theme is "light"

  Scenario: Switching back to "system" restores the OS preference
    Given my system prefers dark
    And I have saved "light" as my theme
    When I open the home page
    Then the document theme is "light"
    When I switch back to the system theme
    And I reload the page
    Then the document theme is "dark"
