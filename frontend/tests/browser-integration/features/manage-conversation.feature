Feature: Manage conversations — reset entry points and deletion

  Scenario: New conversation unpins the document and returns to the empty state
    Given I am signed in viewing a pinned conversation "conv-1" on document "Single_NKE/2010/page_28.pdf"
    When I start a new conversation from the sidebar
    Then the composer shows the "Pin a document first" hint
    And the URL no longer pins a document or a chat

  Scenario: Deleting a conversation removes its row and calls the delete endpoint
    Given I am signed in with a sidebar conversation "conv-del" on document "Double_JKHY/2009/page_28.pdf"
    When I delete the sidebar conversation "conv-del" and confirm
    Then a DELETE request was sent for conversation "conv-del"
    And the sidebar no longer lists conversation "conv-del"
