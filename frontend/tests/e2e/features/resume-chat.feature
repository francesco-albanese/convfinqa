Feature: Resume a persisted conversation

  As a returning user
  I want the app to restore my active conversation across reloads and sidebar clicks
  So I can pick up where I left off and trust the history is real

  Background:
    Given a stubbed backend with a conversation "conv-resume" persisting these messages:
      | role      | content                          |
      | user      | what was the revenue in 2009?    |
      | assistant | Revenue rose to $1.2B in 2009.   |
    And the conversation "conv-resume" is pinned to document "single_NKE/2010/page_X" titled "NKE 2010"

  Scenario: Reload preserves the active chat
    Given I open the app at "/app?chatId=conv-resume&documentId=single_NKE/2010/page_X"
    When I reload the page
    Then I see my message "what was the revenue in 2009?" in the conversation
    And I see the assistant reply containing "Revenue rose to $1.2B in 2009."

  Scenario: Clicking a sidebar entry loads its history
    Given I open the empty app
    When I click the sidebar conversation row for "conv-resume"
    Then I see my message "what was the revenue in 2009?" in the conversation
    And I see the assistant reply containing "Revenue rose to $1.2B in 2009."

  Scenario: A new conversation appears in the sidebar after the stream finishes
    Given a stubbed backend that streams "Revenue rose to $1.2B in 2009." with conversation id "conv-streamed"
    And the just-finished stream is recorded as a new sidebar conversation "conv-streamed" with preview "what was the revenue in 2009?" pinned to document "single_NKE/2010/page_X" titled "NKE 2010"
    And I open the chat with a pinned document "single_NKE/2010/page_X"
    When I type "what was the revenue in 2009?" in the composer
    And I press Cmd+Enter
    Then the sidebar shows a conversation row for "conv-streamed" with the preview "what was the revenue in 2009?"
