// Generated from: tests/browser-integration/features/manage-conversation.feature
import { test } from "playwright-bdd";

test.describe('Manage conversations — reset entry points and deletion', () => {

  test('New conversation unpins the document and returns to the empty state', async ({ Given, When, Then, And, page }) => { 
    await Given('I am signed in viewing a pinned conversation "conv-1" on document "Single_NKE/2010/page_28.pdf"', null, { page }); 
    await When('I start a new conversation from the sidebar', null, { page }); 
    await Then('the composer shows the "Pin a document first" hint', null, { page }); 
    await And('the URL no longer pins a document or a chat', null, { page }); 
  });

  test('Deleting a conversation removes its row and calls the delete endpoint', async ({ Given, When, Then, And, page }) => { 
    await Given('I am signed in with a sidebar conversation "conv-del" on document "Double_JKHY/2009/page_28.pdf"', null, { page }); 
    await When('I delete the sidebar conversation "conv-del" and confirm', null, { page }); 
    await Then('a DELETE request was sent for conversation "conv-del"', null, { page }); 
    await And('the sidebar no longer lists conversation "conv-del"', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/manage-conversation.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":6,"pickleLine":3,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":4,"keywordType":"Context","textWithKeyword":"Given I am signed in viewing a pinned conversation \"conv-1\" on document \"Single_NKE/2010/page_28.pdf\"","stepMatchArguments":[{"group":{"start":45,"value":"\"conv-1\"","children":[{"start":46,"value":"conv-1","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"},{"group":{"start":66,"value":"\"Single_NKE/2010/page_28.pdf\"","children":[{"start":67,"value":"Single_NKE/2010/page_28.pdf","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":8,"gherkinStepLine":5,"keywordType":"Action","textWithKeyword":"When I start a new conversation from the sidebar","stepMatchArguments":[]},{"pwStepLine":9,"gherkinStepLine":6,"keywordType":"Outcome","textWithKeyword":"Then the composer shows the \"Pin a document first\" hint","stepMatchArguments":[{"group":{"start":23,"value":"\"Pin a document first\"","children":[{"start":24,"value":"Pin a document first","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":10,"gherkinStepLine":7,"keywordType":"Outcome","textWithKeyword":"And the URL no longer pins a document or a chat","stepMatchArguments":[]}]},
  {"pwTestLine":13,"pickleLine":9,"tags":[],"steps":[{"pwStepLine":14,"gherkinStepLine":10,"keywordType":"Context","textWithKeyword":"Given I am signed in with a sidebar conversation \"conv-del\" on document \"Double_JKHY/2009/page_28.pdf\"","stepMatchArguments":[{"group":{"start":43,"value":"\"conv-del\"","children":[{"start":44,"value":"conv-del","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"},{"group":{"start":66,"value":"\"Double_JKHY/2009/page_28.pdf\"","children":[{"start":67,"value":"Double_JKHY/2009/page_28.pdf","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":15,"gherkinStepLine":11,"keywordType":"Action","textWithKeyword":"When I delete the sidebar conversation \"conv-del\" and confirm","stepMatchArguments":[{"group":{"start":34,"value":"\"conv-del\"","children":[{"start":35,"value":"conv-del","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":16,"gherkinStepLine":12,"keywordType":"Outcome","textWithKeyword":"Then a DELETE request was sent for conversation \"conv-del\"","stepMatchArguments":[{"group":{"start":43,"value":"\"conv-del\"","children":[{"start":44,"value":"conv-del","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":17,"gherkinStepLine":13,"keywordType":"Outcome","textWithKeyword":"And the sidebar no longer lists conversation \"conv-del\"","stepMatchArguments":[{"group":{"start":41,"value":"\"conv-del\"","children":[{"start":42,"value":"conv-del","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
]; // bdd-data-end