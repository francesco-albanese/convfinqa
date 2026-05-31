Feature: Model switcher — choose which model answers

  Background:
    Given a backend offering models "bedrock/claude-haiku", "gemini/gemini-2.5-flash" defaulting to "bedrock/claude-haiku"
    And I open the chat for model switching with document "Single_NKE/2010/page_28.pdf"

  Scenario: The selected model is sent with the next message
    When I select the model "gemini/gemini-2.5-flash"
    And I send "what was the revenue?" from the composer
    Then the chat stream request used model "gemini/gemini-2.5-flash"

  Scenario: The selected model survives a reload
    When I select the model "gemini/gemini-2.5-flash"
    And I reload the app
    Then the model picker shows "gemini/gemini-2.5-flash"
