Feature: App boot

  As a developer
  I want the SPA to render its landing placeholder on first load
  So that I know the build artifact is wired correctly

  Scenario: Landing route shows the placeholder
    Given I open the home page
    Then I see the "ConvFinQA — coming online" placeholder
