Feature: Send a message and stream the assistant reply

  As a user with a pinned document
  I want to send a question with Cmd+Enter and watch the answer stream in
  So that I can ask follow-ups confident the conversation is captured

  Scenario: Cmd+Enter sends, optimistic bubble appears, assistant text streams in, URL gains chatId
    Given a stubbed backend that streams "Revenue rose to $1.2B in 2009." with conversation id "conv-streamed"
    And I open the chat with a pinned document "single_NKE/2010/page_X"
    When I type "what was the revenue in 2009?" in the composer
    And I press Cmd+Enter
    Then I see my message "what was the revenue in 2009?" in the conversation
    And I see the assistant reply containing "Revenue rose to $1.2B in 2009."
    And the URL contains "chatId=conv-streamed"

  Scenario: Auto-generated conversation title appears in the sidebar
    Given the sidebar already has conversation "conv-titled" with preview "what was the revenue in 2009?"
    And a stubbed backend that streams "Revenue rose to $1.2B in 2009." with conversation id "conv-titled" and title "Revenue overview"
    And I open the chat with a pinned document "single_NKE/2010/page_X"
    When I type "what was the revenue in 2009?" in the composer
    And I press Cmd+Enter
    Then the sidebar conversation "conv-titled" is titled "Revenue overview"

  Scenario: Suggested questions prefill the composer and remaining questions appear after a turn
    Given document "single_NKE/2010/page_X" suggests "what was revenue in 2009?" and "what about 2008?"
    And a stubbed backend that streams "Revenue rose to $1.2B in 2009." with conversation id "conv-suggested"
    And I open the chat with a pinned document "single_NKE/2010/page_X"
    When I choose the suggested question "what was revenue in 2009?"
    Then the composer contains "what was revenue in 2009?"
    When I press Cmd+Enter
    Then I see the follow-up suggestion "what about 2008?"
