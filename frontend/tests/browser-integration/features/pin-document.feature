Feature: Pin a document and render its financial table

  As a signed-in user
  I want to pin a financial document and see its data in the right panel
  So I can ask questions grounded in the document's table and narrative

  Background:
    Given a stubbed backend with the JKHY 2009 page-28-3 document seeded

  Scenario: Pinning shows the table
    Given I open the empty app
    When I open the document picker
    And I pin the JKHY 2009 page-28-3 result
    Then the right panel renders the JKHY 2009 page-28-3 table
    And the table shows the row "net cash from operating activities"

  Scenario: Resize persists across reload
    Given I open the app with the JKHY 2009 page-28-3 document pinned
    When I widen the right panel by four shift-arrow-left presses
    And I reload the page
    Then the right panel is 608 pixels wide

  Scenario: Copy-as-CSV writes the right bytes
    Given I open the app with the JKHY 2009 page-28-3 document pinned
    When I click the "Copy as CSV" button
    Then the clipboard contains the JKHY 2009 page-28-3 CSV bytes

  Scenario: Change document reopens the picker
    Given I open the app with the JKHY 2009 page-28-3 document pinned
    When I click the "Change document" button
    Then the document picker is open
