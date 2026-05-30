// Generated from: tests/browser-integration/features/empty-app.feature
import { test } from "playwright-bdd";

test.describe('Empty app shell', () => {

  test('New user sees the empty state', async ({ Given, Then, And, page }) => { 
    await Given('I open the empty app', null, { page }); 
    await Then('I see the empty-state hero with copy "Pin a document to start chatting"', null, { page }); 
    await And('the right panel is closed', null, { page }); 
  });

  test('Sidebar collapse persists across reload', async ({ Given, When, Then, page }) => { 
    await Given('I open the empty app', null, { page }); 
    await Then('the sidebar is expanded', null, { page }); 
    await When('I collapse the sidebar', null, { page }); 
    await Then('the sidebar is collapsed', null, { page }); 
    await When('I reload the page', null, { page }); 
    await Then('the sidebar is collapsed', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/empty-app.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":6,"pickleLine":7,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given I open the empty app","stepMatchArguments":[]},{"pwStepLine":8,"gherkinStepLine":9,"keywordType":"Outcome","textWithKeyword":"Then I see the empty-state hero with copy \"Pin a document to start chatting\"","stepMatchArguments":[{"group":{"start":37,"value":"\"Pin a document to start chatting\"","children":[{"start":38,"value":"Pin a document to start chatting","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":9,"gherkinStepLine":10,"keywordType":"Outcome","textWithKeyword":"And the right panel is closed","stepMatchArguments":[]}]},
  {"pwTestLine":12,"pickleLine":12,"tags":[],"steps":[{"pwStepLine":13,"gherkinStepLine":13,"keywordType":"Context","textWithKeyword":"Given I open the empty app","stepMatchArguments":[]},{"pwStepLine":14,"gherkinStepLine":14,"keywordType":"Outcome","textWithKeyword":"Then the sidebar is expanded","stepMatchArguments":[]},{"pwStepLine":15,"gherkinStepLine":15,"keywordType":"Action","textWithKeyword":"When I collapse the sidebar","stepMatchArguments":[]},{"pwStepLine":16,"gherkinStepLine":16,"keywordType":"Outcome","textWithKeyword":"Then the sidebar is collapsed","stepMatchArguments":[]},{"pwStepLine":17,"gherkinStepLine":17,"keywordType":"Action","textWithKeyword":"When I reload the page","stepMatchArguments":[]},{"pwStepLine":18,"gherkinStepLine":18,"keywordType":"Outcome","textWithKeyword":"Then the sidebar is collapsed","stepMatchArguments":[]}]},
]; // bdd-data-end