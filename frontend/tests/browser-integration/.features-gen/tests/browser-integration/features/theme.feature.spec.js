// Generated from: tests/browser-integration/features/theme.feature
import { test } from "playwright-bdd";

test.describe('Light/dark theme follows system preference and user override', () => {

  test('Default theme matches the system preference', async ({ Given, When, Then, And, page }) => { 
    await Given('my system prefers light', null, { page }); 
    await And('I have not saved a theme preference', null, { page }); 
    await When('I open the home page', null, { page }); 
    await Then('the document theme is "light"', null, { page }); 
  });

  test('Saved "light" override survives a reload', async ({ Given, When, Then, And, page }) => { 
    await Given('my system prefers dark', null, { page }); 
    await And('I have saved "light" as my theme', null, { page }); 
    await When('I open the home page', null, { page }); 
    await Then('the document theme is "light"', null, { page }); 
    await When('I reload the page', null, { page }); 
    await Then('the document theme is "light"', null, { page }); 
  });

  test('Switching back to "system" restores the OS preference', async ({ Given, When, Then, And, page }) => { 
    await Given('my system prefers dark', null, { page }); 
    await And('I have saved "light" as my theme', null, { page }); 
    await When('I open the home page', null, { page }); 
    await Then('the document theme is "light"', null, { page }); 
    await When('I switch back to the system theme', null, { page }); 
    await And('I reload the page', null, { page }); 
    await Then('the document theme is "dark"', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/theme.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":6,"pickleLine":7,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given my system prefers light","stepMatchArguments":[]},{"pwStepLine":8,"gherkinStepLine":9,"keywordType":"Context","textWithKeyword":"And I have not saved a theme preference","stepMatchArguments":[]},{"pwStepLine":9,"gherkinStepLine":10,"keywordType":"Action","textWithKeyword":"When I open the home page","stepMatchArguments":[]},{"pwStepLine":10,"gherkinStepLine":11,"keywordType":"Outcome","textWithKeyword":"Then the document theme is \"light\"","stepMatchArguments":[{"group":{"start":22,"value":"\"light\"","children":[{"start":23,"value":"light","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
  {"pwTestLine":13,"pickleLine":13,"tags":[],"steps":[{"pwStepLine":14,"gherkinStepLine":14,"keywordType":"Context","textWithKeyword":"Given my system prefers dark","stepMatchArguments":[]},{"pwStepLine":15,"gherkinStepLine":15,"keywordType":"Context","textWithKeyword":"And I have saved \"light\" as my theme","stepMatchArguments":[{"group":{"start":13,"value":"\"light\"","children":[{"start":14,"value":"light","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":16,"gherkinStepLine":16,"keywordType":"Action","textWithKeyword":"When I open the home page","stepMatchArguments":[]},{"pwStepLine":17,"gherkinStepLine":17,"keywordType":"Outcome","textWithKeyword":"Then the document theme is \"light\"","stepMatchArguments":[{"group":{"start":22,"value":"\"light\"","children":[{"start":23,"value":"light","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":18,"gherkinStepLine":18,"keywordType":"Action","textWithKeyword":"When I reload the page","stepMatchArguments":[]},{"pwStepLine":19,"gherkinStepLine":19,"keywordType":"Outcome","textWithKeyword":"Then the document theme is \"light\"","stepMatchArguments":[{"group":{"start":22,"value":"\"light\"","children":[{"start":23,"value":"light","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
  {"pwTestLine":22,"pickleLine":21,"tags":[],"steps":[{"pwStepLine":23,"gherkinStepLine":22,"keywordType":"Context","textWithKeyword":"Given my system prefers dark","stepMatchArguments":[]},{"pwStepLine":24,"gherkinStepLine":23,"keywordType":"Context","textWithKeyword":"And I have saved \"light\" as my theme","stepMatchArguments":[{"group":{"start":13,"value":"\"light\"","children":[{"start":14,"value":"light","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":25,"gherkinStepLine":24,"keywordType":"Action","textWithKeyword":"When I open the home page","stepMatchArguments":[]},{"pwStepLine":26,"gherkinStepLine":25,"keywordType":"Outcome","textWithKeyword":"Then the document theme is \"light\"","stepMatchArguments":[{"group":{"start":22,"value":"\"light\"","children":[{"start":23,"value":"light","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":27,"gherkinStepLine":26,"keywordType":"Action","textWithKeyword":"When I switch back to the system theme","stepMatchArguments":[]},{"pwStepLine":28,"gherkinStepLine":27,"keywordType":"Action","textWithKeyword":"And I reload the page","stepMatchArguments":[]},{"pwStepLine":29,"gherkinStepLine":28,"keywordType":"Outcome","textWithKeyword":"Then the document theme is \"dark\"","stepMatchArguments":[{"group":{"start":22,"value":"\"dark\"","children":[{"start":23,"value":"dark","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
]; // bdd-data-end