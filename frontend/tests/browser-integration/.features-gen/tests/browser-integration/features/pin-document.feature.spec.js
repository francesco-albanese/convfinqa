// Generated from: tests/browser-integration/features/pin-document.feature
import { test } from "playwright-bdd";

test.describe('Pin a document and render its financial table', () => {

  test.beforeEach('Background', async ({ Given, page }, testInfo) => { if (testInfo.error) return;
    await Given('a stubbed backend with the JKHY 2009 page-28-3 document seeded', null, { page }); 
  });
  
  test('Pinning shows the table', async ({ Given, When, Then, And, page }) => { 
    await Given('I open the empty app', null, { page }); 
    await When('I open the document picker', null, { page }); 
    await And('I pin the JKHY 2009 page-28-3 result', null, { page }); 
    await Then('the right panel renders the JKHY 2009 page-28-3 table', null, { page }); 
    await And('the table shows the row "net cash from operating activities"', null, { page }); 
  });

  test('Resize persists across reload', async ({ Given, When, Then, And, page }) => { 
    await Given('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await When('I widen the right panel by four shift-arrow-left presses', null, { page }); 
    await And('I reload the page', null, { page }); 
    await Then('the right panel is 608 pixels wide', null, { page }); 
  });

  test('Copy-as-CSV writes the right bytes', async ({ Given, When, Then, page }) => { 
    await Given('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await When('I click the "Copy as CSV" button', null, { page }); 
    await Then('the clipboard contains the JKHY 2009 page-28-3 CSV bytes', null, { page }); 
  });

  test('Change document reopens the picker', async ({ Given, When, Then, page }) => { 
    await Given('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await When('I click the "Change document" button', null, { page }); 
    await Then('the document picker is open', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/pin-document.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":10,"pickleLine":10,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given a stubbed backend with the JKHY 2009 page-28-3 document seeded","isBg":true,"stepMatchArguments":[]},{"pwStepLine":11,"gherkinStepLine":11,"keywordType":"Context","textWithKeyword":"Given I open the empty app","stepMatchArguments":[]},{"pwStepLine":12,"gherkinStepLine":12,"keywordType":"Action","textWithKeyword":"When I open the document picker","stepMatchArguments":[]},{"pwStepLine":13,"gherkinStepLine":13,"keywordType":"Action","textWithKeyword":"And I pin the JKHY 2009 page-28-3 result","stepMatchArguments":[]},{"pwStepLine":14,"gherkinStepLine":14,"keywordType":"Outcome","textWithKeyword":"Then the right panel renders the JKHY 2009 page-28-3 table","stepMatchArguments":[]},{"pwStepLine":15,"gherkinStepLine":15,"keywordType":"Outcome","textWithKeyword":"And the table shows the row \"net cash from operating activities\"","stepMatchArguments":[{"group":{"start":24,"value":"\"net cash from operating activities\"","children":[{"start":25,"value":"net cash from operating activities","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
  {"pwTestLine":18,"pickleLine":17,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given a stubbed backend with the JKHY 2009 page-28-3 document seeded","isBg":true,"stepMatchArguments":[]},{"pwStepLine":19,"gherkinStepLine":18,"keywordType":"Context","textWithKeyword":"Given I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":20,"gherkinStepLine":19,"keywordType":"Action","textWithKeyword":"When I widen the right panel by four shift-arrow-left presses","stepMatchArguments":[]},{"pwStepLine":21,"gherkinStepLine":20,"keywordType":"Action","textWithKeyword":"And I reload the page","stepMatchArguments":[]},{"pwStepLine":22,"gherkinStepLine":21,"keywordType":"Outcome","textWithKeyword":"Then the right panel is 608 pixels wide","stepMatchArguments":[{"group":{"start":19,"value":"608","children":[]},"parameterTypeName":"int"}]}]},
  {"pwTestLine":25,"pickleLine":23,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given a stubbed backend with the JKHY 2009 page-28-3 document seeded","isBg":true,"stepMatchArguments":[]},{"pwStepLine":26,"gherkinStepLine":24,"keywordType":"Context","textWithKeyword":"Given I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":27,"gherkinStepLine":25,"keywordType":"Action","textWithKeyword":"When I click the \"Copy as CSV\" button","stepMatchArguments":[{"group":{"start":12,"value":"\"Copy as CSV\"","children":[{"start":13,"value":"Copy as CSV","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":28,"gherkinStepLine":26,"keywordType":"Outcome","textWithKeyword":"Then the clipboard contains the JKHY 2009 page-28-3 CSV bytes","stepMatchArguments":[]}]},
  {"pwTestLine":31,"pickleLine":28,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given a stubbed backend with the JKHY 2009 page-28-3 document seeded","isBg":true,"stepMatchArguments":[]},{"pwStepLine":32,"gherkinStepLine":29,"keywordType":"Context","textWithKeyword":"Given I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":33,"gherkinStepLine":30,"keywordType":"Action","textWithKeyword":"When I click the \"Change document\" button","stepMatchArguments":[{"group":{"start":12,"value":"\"Change document\"","children":[{"start":13,"value":"Change document","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":34,"gherkinStepLine":31,"keywordType":"Outcome","textWithKeyword":"Then the document picker is open","stepMatchArguments":[]}]},
]; // bdd-data-end