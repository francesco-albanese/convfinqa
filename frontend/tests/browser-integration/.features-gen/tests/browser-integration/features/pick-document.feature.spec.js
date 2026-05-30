// Generated from: tests/browser-integration/features/pick-document.feature
import { test } from "playwright-bdd";

test.describe('Document picker — search, filter, and pin via URL', () => {

  test.beforeEach('Background', async ({ Given, page }, testInfo) => { if (testInfo.error) return;
    await Given('a stubbed backend with 20 deterministic documents seeded', null, { page }); 
  });
  
  test('Search by ticker', async ({ Given, When, Then, And, page }) => { 
    await Given('I open the empty app', null, { page }); 
    await When('I open the document picker', null, { page }); 
    await And('I type "AAPL" into the document search', null, { page }); 
    await Then('the picker shows only documents with ticker "AAPL"', null, { page }); 
  });

  test('Narrow by year', async ({ Given, When, Then, And, page }) => { 
    await Given('I open the empty app', null, { page }); 
    await When('I open the document picker', null, { page }); 
    await And('I narrow the year range to 2012 through 2014', null, { page }); 
    await Then('the picker shows only documents whose year is between 2012 and 2014', null, { page }); 
  });

  test('Pin a result via URL param', async ({ Given, When, Then, And, page }) => { 
    await Given('I open the empty app', null, { page }); 
    await When('I open the document picker', null, { page }); 
    await And('I pin the first picker result', null, { page }); 
    await Then('the URL has the documentId search param set to the first picker result\'s id', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/pick-document.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":10,"pickleLine":10,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given a stubbed backend with 20 deterministic documents seeded","isBg":true,"stepMatchArguments":[]},{"pwStepLine":11,"gherkinStepLine":11,"keywordType":"Context","textWithKeyword":"Given I open the empty app","stepMatchArguments":[]},{"pwStepLine":12,"gherkinStepLine":12,"keywordType":"Action","textWithKeyword":"When I open the document picker","stepMatchArguments":[]},{"pwStepLine":13,"gherkinStepLine":13,"keywordType":"Action","textWithKeyword":"And I type \"AAPL\" into the document search","stepMatchArguments":[{"group":{"start":7,"value":"\"AAPL\"","children":[{"start":8,"value":"AAPL","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]},{"pwStepLine":14,"gherkinStepLine":14,"keywordType":"Outcome","textWithKeyword":"Then the picker shows only documents with ticker \"AAPL\"","stepMatchArguments":[{"group":{"start":44,"value":"\"AAPL\"","children":[{"start":45,"value":"AAPL","children":[{"children":[]}]},{"children":[{"children":[]}]}]},"parameterTypeName":"string"}]}]},
  {"pwTestLine":17,"pickleLine":16,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given a stubbed backend with 20 deterministic documents seeded","isBg":true,"stepMatchArguments":[]},{"pwStepLine":18,"gherkinStepLine":17,"keywordType":"Context","textWithKeyword":"Given I open the empty app","stepMatchArguments":[]},{"pwStepLine":19,"gherkinStepLine":18,"keywordType":"Action","textWithKeyword":"When I open the document picker","stepMatchArguments":[]},{"pwStepLine":20,"gherkinStepLine":19,"keywordType":"Action","textWithKeyword":"And I narrow the year range to 2012 through 2014","stepMatchArguments":[{"group":{"start":27,"value":"2012","children":[]},"parameterTypeName":"int"},{"group":{"start":40,"value":"2014","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":21,"gherkinStepLine":20,"keywordType":"Outcome","textWithKeyword":"Then the picker shows only documents whose year is between 2012 and 2014","stepMatchArguments":[{"group":{"start":54,"value":"2012","children":[]},"parameterTypeName":"int"},{"group":{"start":63,"value":"2014","children":[]},"parameterTypeName":"int"}]}]},
  {"pwTestLine":24,"pickleLine":22,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given a stubbed backend with 20 deterministic documents seeded","isBg":true,"stepMatchArguments":[]},{"pwStepLine":25,"gherkinStepLine":23,"keywordType":"Context","textWithKeyword":"Given I open the empty app","stepMatchArguments":[]},{"pwStepLine":26,"gherkinStepLine":24,"keywordType":"Action","textWithKeyword":"When I open the document picker","stepMatchArguments":[]},{"pwStepLine":27,"gherkinStepLine":25,"keywordType":"Action","textWithKeyword":"And I pin the first picker result","stepMatchArguments":[]},{"pwStepLine":28,"gherkinStepLine":26,"keywordType":"Outcome","textWithKeyword":"Then the URL has the documentId search param set to the first picker result's id","stepMatchArguments":[]}]},
]; // bdd-data-end