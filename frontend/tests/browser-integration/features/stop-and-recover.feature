@stop-recover
Feature: Stop a streaming reply and recover from a 409 conflict

  As a user mid-stream
  I want to halt a long reply and recover from a conversation-busy error
  So that I stay in control of the conversation

  Scenario: Stop preserves the partial assistant reply
    Given I open the chat with a pinned document "single_NKE/2010/page_X"
    And the next chat stream emits "Revenue rose to" then holds
    When I type "what was the revenue in 2009?" in the composer
    And I press Cmd+Enter
    And I see the assistant reply containing "Revenue rose to"
    And I click the stop button
    Then I see the assistant reply containing "Revenue rose to"
    And the assistant message shows a "Stopped" badge

  Scenario: A 409 conflict surfaces an inline banner with a retry button
    Given I open the chat with a pinned document "single_NKE/2010/page_X"
    And the next chat stream responds with a 409 conflict
    When I type "another follow-up" in the composer
    And I press Cmd+Enter
    Then I see the stream error banner with title "Another response is in progress"
    And I see the retry button on the banner

  Scenario: Retry completes the next stream after a 409
    Given I open the chat with a pinned document "single_NKE/2010/page_X"
    And the next chat stream responds with a 409 conflict
    And the chat stream after that emits "Operating margin held at 20%." in one chunk
    When I type "and the margin?" in the composer
    And I press Cmd+Enter
    And I see the stream error banner with title "Another response is in progress"
    And I click the retry button on the banner
    Then I see the assistant reply containing "Operating margin held at 20%."
    And the stream error banner is gone
