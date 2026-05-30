// Generated from: tests/browser-integration/features/stop-and-recover.feature
import { test } from "playwright-bdd";

test.describe('Stop a streaming reply and recover from a 409 conflict', () => {

  test('Stop preserves the partial assistant reply', { tag: ['@stop-recover'] }, async ({ Given, When, Then, And, page }) => { 
    await Given('I open the chat with a pinned document "single_NKE/2010/page_X"', null, { page }); 
    await And('the next chat stream emits "Revenue rose to" then holds', null, { page }); 
    await When('I type "what was the revenue in 2009?" in the composer', null, { page }); 
    await And('I press Cmd+Enter', null, { page }); 
    await And('I see the assistant reply containing "Revenue rose to"', null, { page }); 
    await And('I click the stop button', null, { page }); 
    await Then('I see the assistant reply containing "Revenue rose to"', null, { page }); 
    await And('the assistant message shows a "Stopped" badge', null, { page }); 
  });

  test('A 409 conflict surfaces an inline banner with a retry button', { tag: ['@stop-recover'] }, async ({ Given, When, Then, And, page }) => { 
    await Given('I open the chat with a pinned document "single_NKE/2010/page_X"', null, { page }); 
    await And('the next chat stream responds with a 409 conflict', null, { page }); 
    await When('I type "another follow-up" in the composer', null, { page }); 
    await And('I press Cmd+Enter', null, { page }); 
    await Then('I see the stream error banner with title "Another response is in progress"', null, { page }); 
    await And('I see the retry button on the banner', null, { page }); 
  });

  test('Retry completes the next stream after a 409', { tag: ['@stop-recover'] }, async ({ Given, When, Then, And, page }) => { 
    await Given('I open the chat with a pinned document "single_NKE/2010/page_X"', null, { page }); 
    await And('the next chat stream responds with a 409 conflict', null, { page }); 
    await And('the chat stream after that emits "Operating margin held at 20%." in one chunk', null, { page }); 
    await When('I type "and the margin?" in the composer', null, { page }); 
    await And('I press Cmd+Enter', null, { page }); 
    await And('I see the stream error banner with title "Another response is in progress"', null, { page }); 
    await And('I click the retry button on the banner', null, { page }); 
    await Then('I see the assistant reply containing "Operating margin held at 20%."', null, { page }); 
    await And('the stream error banner is gone', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks, page }) => $runScenarioHooks('before', { page }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/stop-and-recover.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":6,"pickleLine":8,"tags":["@stop-recover"],"steps":[{"pwStepLine":7,"gherkinStepLine":9,"keywordType":"Context","textWithKeyword":"Given I open the chat with a pinned document \"single_NKE/2010/page_X\"","stepMatchArguments":[{"group":{"start":39,"value":"\"single_NKE/2010/page_X\"","children":[{"start":40,"value":"single_NKE/2010/page_X","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":8,"gherkinStepLine":10,"keywordType":"Context","textWithKeyword":"And the next chat stream emits \"Revenue rose to\" then holds","stepMatchArguments":[{"group":{"start":27,"value":"\"Revenue rose to\"","children":[{"start":28,"value":"Revenue rose to","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":9,"gherkinStepLine":11,"keywordType":"Action","textWithKeyword":"When I type \"what was the revenue in 2009?\" in the composer","stepMatchArguments":[{"group":{"start":7,"value":"\"what was the revenue in 2009?\"","children":[{"start":8,"value":"what was the revenue in 2009?","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":10,"gherkinStepLine":12,"keywordType":"Action","textWithKeyword":"And I press Cmd+Enter","stepMatchArguments":[]},{"pwStepLine":11,"gherkinStepLine":13,"keywordType":"Action","textWithKeyword":"And I see the assistant reply containing \"Revenue rose to\"","stepMatchArguments":[{"group":{"start":37,"value":"\"Revenue rose to\"","children":[{"start":38,"value":"Revenue rose to","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":12,"gherkinStepLine":14,"keywordType":"Action","textWithKeyword":"And I click the stop button","stepMatchArguments":[]},{"pwStepLine":13,"gherkinStepLine":15,"keywordType":"Outcome","textWithKeyword":"Then I see the assistant reply containing \"Revenue rose to\"","stepMatchArguments":[{"group":{"start":37,"value":"\"Revenue rose to\"","children":[{"start":38,"value":"Revenue rose to","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":14,"gherkinStepLine":16,"keywordType":"Outcome","textWithKeyword":"And the assistant message shows a \"Stopped\" badge","stepMatchArguments":[{"group":{"start":30,"value":"\"Stopped\"","children":[{"start":31,"value":"Stopped","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
  {"pwTestLine":17,"pickleLine":18,"tags":["@stop-recover"],"steps":[{"pwStepLine":18,"gherkinStepLine":19,"keywordType":"Context","textWithKeyword":"Given I open the chat with a pinned document \"single_NKE/2010/page_X\"","stepMatchArguments":[{"group":{"start":39,"value":"\"single_NKE/2010/page_X\"","children":[{"start":40,"value":"single_NKE/2010/page_X","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":19,"gherkinStepLine":20,"keywordType":"Context","textWithKeyword":"And the next chat stream responds with a 409 conflict","stepMatchArguments":[]},{"pwStepLine":20,"gherkinStepLine":21,"keywordType":"Action","textWithKeyword":"When I type \"another follow-up\" in the composer","stepMatchArguments":[{"group":{"start":7,"value":"\"another follow-up\"","children":[{"start":8,"value":"another follow-up","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":21,"gherkinStepLine":22,"keywordType":"Action","textWithKeyword":"And I press Cmd+Enter","stepMatchArguments":[]},{"pwStepLine":22,"gherkinStepLine":23,"keywordType":"Outcome","textWithKeyword":"Then I see the stream error banner with title \"Another response is in progress\"","stepMatchArguments":[{"group":{"start":41,"value":"\"Another response is in progress\"","children":[{"start":42,"value":"Another response is in progress","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":23,"gherkinStepLine":24,"keywordType":"Outcome","textWithKeyword":"And I see the retry button on the banner","stepMatchArguments":[]}]},
  {"pwTestLine":26,"pickleLine":26,"tags":["@stop-recover"],"steps":[{"pwStepLine":27,"gherkinStepLine":27,"keywordType":"Context","textWithKeyword":"Given I open the chat with a pinned document \"single_NKE/2010/page_X\"","stepMatchArguments":[{"group":{"start":39,"value":"\"single_NKE/2010/page_X\"","children":[{"start":40,"value":"single_NKE/2010/page_X","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":28,"gherkinStepLine":28,"keywordType":"Context","textWithKeyword":"And the next chat stream responds with a 409 conflict","stepMatchArguments":[]},{"pwStepLine":29,"gherkinStepLine":29,"keywordType":"Context","textWithKeyword":"And the chat stream after that emits \"Operating margin held at 20%.\" in one chunk","stepMatchArguments":[{"group":{"start":33,"value":"\"Operating margin held at 20%.\"","children":[{"start":34,"value":"Operating margin held at 20%.","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":30,"gherkinStepLine":30,"keywordType":"Action","textWithKeyword":"When I type \"and the margin?\" in the composer","stepMatchArguments":[{"group":{"start":7,"value":"\"and the margin?\"","children":[{"start":8,"value":"and the margin?","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":31,"gherkinStepLine":31,"keywordType":"Action","textWithKeyword":"And I press Cmd+Enter","stepMatchArguments":[]},{"pwStepLine":32,"gherkinStepLine":32,"keywordType":"Action","textWithKeyword":"And I see the stream error banner with title \"Another response is in progress\"","stepMatchArguments":[{"group":{"start":41,"value":"\"Another response is in progress\"","children":[{"start":42,"value":"Another response is in progress","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":33,"gherkinStepLine":33,"keywordType":"Action","textWithKeyword":"And I click the retry button on the banner","stepMatchArguments":[]},{"pwStepLine":34,"gherkinStepLine":34,"keywordType":"Outcome","textWithKeyword":"Then I see the assistant reply containing \"Operating margin held at 20%.\"","stepMatchArguments":[{"group":{"start":37,"value":"\"Operating margin held at 20%.\"","children":[{"start":38,"value":"Operating margin held at 20%.","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":35,"gherkinStepLine":35,"keywordType":"Outcome","textWithKeyword":"And the stream error banner is gone","stepMatchArguments":[]}]},
]; // bdd-data-end