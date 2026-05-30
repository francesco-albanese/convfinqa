// Generated from: tests/browser-integration/features/model-switcher.feature
import { test } from "playwright-bdd";

test.describe('Model switcher — choose which model answers', () => {

  test.beforeEach('Background', async ({ Given, And, page }, testInfo) => { if (testInfo.error) return;
    await Given('a backend offering models "bedrock/claude-haiku", "gemini/gemini-2.5-flash" defaulting to "bedrock/claude-haiku"', null, { page }); 
    await And('I open the chat for model switching with document "Single_NKE/2010/page_28.pdf"', null, { page }); 
  });
  
  test('The selected model is sent with the next message', async ({ When, Then, And, page }) => { 
    await When('I select the model "gemini/gemini-2.5-flash"', null, { page }); 
    await And('I send "what was the revenue?" from the composer', null, { page }); 
    await Then('the chat stream request used model "gemini/gemini-2.5-flash"', null, { page }); 
  });

  test('The selected model survives a reload', async ({ When, Then, And, page }) => { 
    await When('I select the model "gemini/gemini-2.5-flash"', null, { page }); 
    await And('I reload the app', null, { page }); 
    await Then('the model picker shows "gemini/gemini-2.5-flash"', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/model-switcher.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":11,"pickleLine":7,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":4,"keywordType":"Context","textWithKeyword":"Given a backend offering models \"bedrock/claude-haiku\", \"gemini/gemini-2.5-flash\" defaulting to \"bedrock/claude-haiku\"","isBg":true,"stepMatchArguments":[{"group":{"start":26,"value":"\"bedrock/claude-haiku\"","children":[{"start":27,"value":"bedrock/claude-haiku","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"},{"group":{"start":50,"value":"\"gemini/gemini-2.5-flash\"","children":[{"start":51,"value":"gemini/gemini-2.5-flash","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"},{"group":{"start":90,"value":"\"bedrock/claude-haiku\"","children":[{"start":91,"value":"bedrock/claude-haiku","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":8,"gherkinStepLine":5,"keywordType":"Context","textWithKeyword":"And I open the chat for model switching with document \"Single_NKE/2010/page_28.pdf\"","isBg":true,"stepMatchArguments":[{"group":{"start":50,"value":"\"Single_NKE/2010/page_28.pdf\"","children":[{"start":51,"value":"Single_NKE/2010/page_28.pdf","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":12,"gherkinStepLine":8,"keywordType":"Action","textWithKeyword":"When I select the model \"gemini/gemini-2.5-flash\"","stepMatchArguments":[{"group":{"start":19,"value":"\"gemini/gemini-2.5-flash\"","children":[{"start":20,"value":"gemini/gemini-2.5-flash","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":13,"gherkinStepLine":9,"keywordType":"Action","textWithKeyword":"And I send \"what was the revenue?\" from the composer","stepMatchArguments":[{"group":{"start":7,"value":"\"what was the revenue?\"","children":[{"start":8,"value":"what was the revenue?","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":14,"gherkinStepLine":10,"keywordType":"Outcome","textWithKeyword":"Then the chat stream request used model \"gemini/gemini-2.5-flash\"","stepMatchArguments":[{"group":{"start":35,"value":"\"gemini/gemini-2.5-flash\"","children":[{"start":36,"value":"gemini/gemini-2.5-flash","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
  {"pwTestLine":17,"pickleLine":12,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":4,"keywordType":"Context","textWithKeyword":"Given a backend offering models \"bedrock/claude-haiku\", \"gemini/gemini-2.5-flash\" defaulting to \"bedrock/claude-haiku\"","isBg":true,"stepMatchArguments":[{"group":{"start":26,"value":"\"bedrock/claude-haiku\"","children":[{"start":27,"value":"bedrock/claude-haiku","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"},{"group":{"start":50,"value":"\"gemini/gemini-2.5-flash\"","children":[{"start":51,"value":"gemini/gemini-2.5-flash","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"},{"group":{"start":90,"value":"\"bedrock/claude-haiku\"","children":[{"start":91,"value":"bedrock/claude-haiku","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":8,"gherkinStepLine":5,"keywordType":"Context","textWithKeyword":"And I open the chat for model switching with document \"Single_NKE/2010/page_28.pdf\"","isBg":true,"stepMatchArguments":[{"group":{"start":50,"value":"\"Single_NKE/2010/page_28.pdf\"","children":[{"start":51,"value":"Single_NKE/2010/page_28.pdf","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":18,"gherkinStepLine":13,"keywordType":"Action","textWithKeyword":"When I select the model \"gemini/gemini-2.5-flash\"","stepMatchArguments":[{"group":{"start":19,"value":"\"gemini/gemini-2.5-flash\"","children":[{"start":20,"value":"gemini/gemini-2.5-flash","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":19,"gherkinStepLine":14,"keywordType":"Action","textWithKeyword":"And I reload the app","stepMatchArguments":[]},{"pwStepLine":20,"gherkinStepLine":15,"keywordType":"Outcome","textWithKeyword":"Then the model picker shows \"gemini/gemini-2.5-flash\"","stepMatchArguments":[{"group":{"start":23,"value":"\"gemini/gemini-2.5-flash\"","children":[{"start":24,"value":"gemini/gemini-2.5-flash","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
]; // bdd-data-end