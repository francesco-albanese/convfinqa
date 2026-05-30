// Generated from: tests/browser-integration/features/auth.feature
import { test } from "playwright-bdd";

test.describe('Auth session', () => {

  test('Sign out clears the session and returns to /sign-in', async ({ Given, When, Then, And, page }) => { 
    await Given('I am signed in on the app page', null, { page }); 
    await When('I open the user menu', null, { page }); 
    await And('I select the "Sign out" menu item', null, { page }); 
    await Then('I land on the sign-in page', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/auth.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":6,"pickleLine":7,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given I am signed in on the app page","stepMatchArguments":[]},{"pwStepLine":8,"gherkinStepLine":9,"keywordType":"Action","textWithKeyword":"When I open the user menu","stepMatchArguments":[]},{"pwStepLine":9,"gherkinStepLine":10,"keywordType":"Action","textWithKeyword":"And I select the \"Sign out\" menu item","stepMatchArguments":[{"group":{"start":13,"value":"\"Sign out\"","children":[{"start":14,"value":"Sign out","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":10,"gherkinStepLine":11,"keywordType":"Outcome","textWithKeyword":"Then I land on the sign-in page","stepMatchArguments":[]}]},
]; // bdd-data-end