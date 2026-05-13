Feature: Document picker — search, filter, and pin via URL

  As a signed-in user
  I want to search and filter the document library
  So I can find and pin the right document to chat about

  Background:
    Given a stubbed backend with 20 deterministic documents seeded

  Scenario: Search by ticker
    Given I open the empty app
    When I open the document picker
    And I type "AAPL" into the document search
    Then the picker shows only documents with ticker "AAPL"

  Scenario: Narrow by year
    Given I open the empty app
    When I open the document picker
    And I narrow the year range to 2012 through 2014
    Then the picker shows only documents whose year is between 2012 and 2014

  Scenario: Pin a result via URL param
    Given I open the empty app
    When I open the document picker
    And I pin the first picker result
    Then the URL has the documentId search param set to the first picker result's id
