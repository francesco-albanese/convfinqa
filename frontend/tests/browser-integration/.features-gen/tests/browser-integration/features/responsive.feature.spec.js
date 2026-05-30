// Generated from: tests/browser-integration/features/responsive.feature
import { test } from "playwright-bdd";

test.describe('Responsive sidebar drawer', () => {

  test('600px viewport — sidebar drawer + bottom sheet', async ({ Given, When, Then, And, page }) => { 
    await Given('my viewport is 600 by 900', null, { page }); 
    await And('a stubbed backend with the JKHY 2009 page-28-3 document seeded', null, { page }); 
    await And('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await Then('the hamburger button is visible', null, { page }); 
    await And('the View document button is visible', null, { page }); 
    await And('the sidebar drawer is closed', null, { page }); 
    await And('the right panel sheet is closed', null, { page }); 
    await And('the layout has no horizontal scrollbar', null, { page }); 
    await When('I open the sidebar drawer', null, { page }); 
    await Then('the sidebar drawer is open', null, { page }); 
    await When('I dismiss the sidebar drawer by clicking the backdrop', null, { page }); 
    await Then('the sidebar drawer is closed', null, { page }); 
    await When('I click the View document button', null, { page }); 
    await Then('the right panel sheet is open', null, { page }); 
    await When('I dismiss the right panel sheet via the close button', null, { page }); 
    await Then('the right panel sheet is closed', null, { page }); 
    await And('the layout has no horizontal scrollbar', null, { page }); 
  });

  test('900px viewport — same behavior', async ({ Given, When, Then, And, page }) => { 
    await Given('my viewport is 900 by 800', null, { page }); 
    await And('a stubbed backend with the JKHY 2009 page-28-3 document seeded', null, { page }); 
    await And('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await Then('the hamburger button is visible', null, { page }); 
    await And('the View document button is visible', null, { page }); 
    await And('the sidebar drawer is closed', null, { page }); 
    await And('the right panel sheet is closed', null, { page }); 
    await When('I open the sidebar drawer', null, { page }); 
    await Then('the sidebar drawer is open', null, { page }); 
    await When('I dismiss the sidebar drawer by clicking the backdrop', null, { page }); 
    await Then('the sidebar drawer is closed', null, { page }); 
    await When('I click the View document button', null, { page }); 
    await Then('the right panel sheet is open', null, { page }); 
    await When('I dismiss the right panel sheet via the close button', null, { page }); 
    await Then('the right panel sheet is closed', null, { page }); 
  });

  test('Below 1024px, the hamburger toggles the sidebar drawer', async ({ Given, When, Then, And, page }) => { 
    await Given('my viewport is 800 by 800', null, { page }); 
    await And('I open the empty app', null, { page }); 
    await Then('the hamburger button is visible', null, { page }); 
    await And('the sidebar drawer is closed', null, { page }); 
    await When('I open the sidebar drawer', null, { page }); 
    await Then('the sidebar drawer is open', null, { page }); 
    await When('I dismiss the sidebar drawer by clicking the backdrop', null, { page }); 
    await Then('the sidebar drawer is closed', null, { page }); 
  });

  test('At 1280px the hamburger is hidden and the sidebar is always visible', async ({ Given, Then, And, page }) => { 
    await Given('my viewport is 1280 by 800', null, { page }); 
    await And('I open the empty app', null, { page }); 
    await Then('the hamburger button is hidden', null, { page }); 
    await And('the sidebar is visible', null, { page }); 
  });

  test('Below 1024px with a pinned document, the View document button opens a bottom sheet', async ({ Given, When, Then, And, page }) => { 
    await Given('my viewport is 600 by 900', null, { page }); 
    await And('a stubbed backend with the JKHY 2009 page-28-3 document seeded', null, { page }); 
    await And('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await Then('the View document button is visible', null, { page }); 
    await And('the right panel sheet is closed', null, { page }); 
    await When('I click the View document button', null, { page }); 
    await Then('the right panel sheet is open', null, { page }); 
    await When('I dismiss the right panel sheet via the close button', null, { page }); 
    await Then('the right panel sheet is closed', null, { page }); 
  });

  test('At 1280px with a pinned document, no View document button is shown', async ({ Given, Then, And, page }) => { 
    await Given('my viewport is 1280 by 800', null, { page }); 
    await And('a stubbed backend with the JKHY 2009 page-28-3 document seeded', null, { page }); 
    await And('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await Then('the View document button is hidden', null, { page }); 
  });

  test('Below lg, Escape closes the sidebar drawer and returns focus to the hamburger', async ({ Given, When, Then, And, page }) => { 
    await Given('my viewport is 600 by 900', null, { page }); 
    await And('I open the empty app', null, { page }); 
    await When('I open the sidebar drawer', null, { page }); 
    await Then('the sidebar drawer is open', null, { page }); 
    await And('the sidebar drawer has role dialog and aria-modal true', null, { page }); 
    await When('I press Escape', null, { page }); 
    await Then('the sidebar drawer is closed', null, { page }); 
    await And('the hamburger button has focus', null, { page }); 
  });

  test('Below lg, Escape closes the right-panel sheet and returns focus to the trigger', async ({ Given, When, Then, And, page }) => { 
    await Given('my viewport is 600 by 900', null, { page }); 
    await And('a stubbed backend with the JKHY 2009 page-28-3 document seeded', null, { page }); 
    await And('I open the app with the JKHY 2009 page-28-3 document pinned', null, { page }); 
    await When('I click the View document button', null, { page }); 
    await Then('the right panel sheet is open', null, { page }); 
    await And('the right panel sheet has role dialog and aria-modal true', null, { page }); 
    await When('I press Escape', null, { page }); 
    await Then('the right panel sheet is closed', null, { page }); 
    await And('the View document button has focus', null, { page }); 
  });

});

// == technical section ==

test.beforeEach('BeforeEach Hooks', ({ $runScenarioHooks }) => $runScenarioHooks('before', {  }));

test.use({
  $test: [({}, use) => use(test), { scope: 'test', box: true }],
  $uri: [({}, use) => use('tests/browser-integration/features/responsive.feature'), { scope: 'test', box: true }],
  $bddFileData: [({}, use) => use(bddFileData), { scope: "test", box: true }],
});

const bddFileData = [ // bdd-data-start
  {"pwTestLine":6,"pickleLine":7,"tags":[],"steps":[{"pwStepLine":7,"gherkinStepLine":8,"keywordType":"Context","textWithKeyword":"Given my viewport is 600 by 900","stepMatchArguments":[{"group":{"start":15,"value":"600","children":[]},"parameterTypeName":"int"},{"group":{"start":22,"value":"900","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":8,"gherkinStepLine":9,"keywordType":"Context","textWithKeyword":"And a stubbed backend with the JKHY 2009 page-28-3 document seeded","stepMatchArguments":[]},{"pwStepLine":9,"gherkinStepLine":10,"keywordType":"Context","textWithKeyword":"And I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":10,"gherkinStepLine":11,"keywordType":"Outcome","textWithKeyword":"Then the hamburger button is visible","stepMatchArguments":[]},{"pwStepLine":11,"gherkinStepLine":12,"keywordType":"Outcome","textWithKeyword":"And the View document button is visible","stepMatchArguments":[]},{"pwStepLine":12,"gherkinStepLine":13,"keywordType":"Outcome","textWithKeyword":"And the sidebar drawer is closed","stepMatchArguments":[]},{"pwStepLine":13,"gherkinStepLine":14,"keywordType":"Outcome","textWithKeyword":"And the right panel sheet is closed","stepMatchArguments":[]},{"pwStepLine":14,"gherkinStepLine":15,"keywordType":"Outcome","textWithKeyword":"And the layout has no horizontal scrollbar","stepMatchArguments":[]},{"pwStepLine":15,"gherkinStepLine":16,"keywordType":"Action","textWithKeyword":"When I open the sidebar drawer","stepMatchArguments":[]},{"pwStepLine":16,"gherkinStepLine":17,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is open","stepMatchArguments":[]},{"pwStepLine":17,"gherkinStepLine":18,"keywordType":"Action","textWithKeyword":"When I dismiss the sidebar drawer by clicking the backdrop","stepMatchArguments":[]},{"pwStepLine":18,"gherkinStepLine":19,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is closed","stepMatchArguments":[]},{"pwStepLine":19,"gherkinStepLine":20,"keywordType":"Action","textWithKeyword":"When I click the View document button","stepMatchArguments":[]},{"pwStepLine":20,"gherkinStepLine":21,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is open","stepMatchArguments":[]},{"pwStepLine":21,"gherkinStepLine":22,"keywordType":"Action","textWithKeyword":"When I dismiss the right panel sheet via the close button","stepMatchArguments":[]},{"pwStepLine":22,"gherkinStepLine":23,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is closed","stepMatchArguments":[]},{"pwStepLine":23,"gherkinStepLine":24,"keywordType":"Outcome","textWithKeyword":"And the layout has no horizontal scrollbar","stepMatchArguments":[]}]},
  {"pwTestLine":26,"pickleLine":26,"tags":[],"steps":[{"pwStepLine":27,"gherkinStepLine":27,"keywordType":"Context","textWithKeyword":"Given my viewport is 900 by 800","stepMatchArguments":[{"group":{"start":15,"value":"900","children":[]},"parameterTypeName":"int"},{"group":{"start":22,"value":"800","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":28,"gherkinStepLine":28,"keywordType":"Context","textWithKeyword":"And a stubbed backend with the JKHY 2009 page-28-3 document seeded","stepMatchArguments":[]},{"pwStepLine":29,"gherkinStepLine":29,"keywordType":"Context","textWithKeyword":"And I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":30,"gherkinStepLine":30,"keywordType":"Outcome","textWithKeyword":"Then the hamburger button is visible","stepMatchArguments":[]},{"pwStepLine":31,"gherkinStepLine":31,"keywordType":"Outcome","textWithKeyword":"And the View document button is visible","stepMatchArguments":[]},{"pwStepLine":32,"gherkinStepLine":32,"keywordType":"Outcome","textWithKeyword":"And the sidebar drawer is closed","stepMatchArguments":[]},{"pwStepLine":33,"gherkinStepLine":33,"keywordType":"Outcome","textWithKeyword":"And the right panel sheet is closed","stepMatchArguments":[]},{"pwStepLine":34,"gherkinStepLine":34,"keywordType":"Action","textWithKeyword":"When I open the sidebar drawer","stepMatchArguments":[]},{"pwStepLine":35,"gherkinStepLine":35,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is open","stepMatchArguments":[]},{"pwStepLine":36,"gherkinStepLine":36,"keywordType":"Action","textWithKeyword":"When I dismiss the sidebar drawer by clicking the backdrop","stepMatchArguments":[]},{"pwStepLine":37,"gherkinStepLine":37,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is closed","stepMatchArguments":[]},{"pwStepLine":38,"gherkinStepLine":38,"keywordType":"Action","textWithKeyword":"When I click the View document button","stepMatchArguments":[]},{"pwStepLine":39,"gherkinStepLine":39,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is open","stepMatchArguments":[]},{"pwStepLine":40,"gherkinStepLine":40,"keywordType":"Action","textWithKeyword":"When I dismiss the right panel sheet via the close button","stepMatchArguments":[]},{"pwStepLine":41,"gherkinStepLine":41,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is closed","stepMatchArguments":[]}]},
  {"pwTestLine":44,"pickleLine":43,"tags":[],"steps":[{"pwStepLine":45,"gherkinStepLine":44,"keywordType":"Context","textWithKeyword":"Given my viewport is 800 by 800","stepMatchArguments":[{"group":{"start":15,"value":"800","children":[]},"parameterTypeName":"int"},{"group":{"start":22,"value":"800","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":46,"gherkinStepLine":45,"keywordType":"Context","textWithKeyword":"And I open the empty app","stepMatchArguments":[]},{"pwStepLine":47,"gherkinStepLine":46,"keywordType":"Outcome","textWithKeyword":"Then the hamburger button is visible","stepMatchArguments":[]},{"pwStepLine":48,"gherkinStepLine":47,"keywordType":"Outcome","textWithKeyword":"And the sidebar drawer is closed","stepMatchArguments":[]},{"pwStepLine":49,"gherkinStepLine":48,"keywordType":"Action","textWithKeyword":"When I open the sidebar drawer","stepMatchArguments":[]},{"pwStepLine":50,"gherkinStepLine":49,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is open","stepMatchArguments":[]},{"pwStepLine":51,"gherkinStepLine":50,"keywordType":"Action","textWithKeyword":"When I dismiss the sidebar drawer by clicking the backdrop","stepMatchArguments":[]},{"pwStepLine":52,"gherkinStepLine":51,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is closed","stepMatchArguments":[]}]},
  {"pwTestLine":55,"pickleLine":53,"tags":[],"steps":[{"pwStepLine":56,"gherkinStepLine":54,"keywordType":"Context","textWithKeyword":"Given my viewport is 1280 by 800","stepMatchArguments":[{"group":{"start":15,"value":"1280","children":[]},"parameterTypeName":"int"},{"group":{"start":23,"value":"800","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":57,"gherkinStepLine":55,"keywordType":"Context","textWithKeyword":"And I open the empty app","stepMatchArguments":[]},{"pwStepLine":58,"gherkinStepLine":56,"keywordType":"Outcome","textWithKeyword":"Then the hamburger button is hidden","stepMatchArguments":[]},{"pwStepLine":59,"gherkinStepLine":57,"keywordType":"Outcome","textWithKeyword":"And the sidebar is visible","stepMatchArguments":[]}]},
  {"pwTestLine":62,"pickleLine":59,"tags":[],"steps":[{"pwStepLine":63,"gherkinStepLine":60,"keywordType":"Context","textWithKeyword":"Given my viewport is 600 by 900","stepMatchArguments":[{"group":{"start":15,"value":"600","children":[]},"parameterTypeName":"int"},{"group":{"start":22,"value":"900","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":64,"gherkinStepLine":61,"keywordType":"Context","textWithKeyword":"And a stubbed backend with the JKHY 2009 page-28-3 document seeded","stepMatchArguments":[]},{"pwStepLine":65,"gherkinStepLine":62,"keywordType":"Context","textWithKeyword":"And I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":66,"gherkinStepLine":63,"keywordType":"Outcome","textWithKeyword":"Then the View document button is visible","stepMatchArguments":[]},{"pwStepLine":67,"gherkinStepLine":64,"keywordType":"Outcome","textWithKeyword":"And the right panel sheet is closed","stepMatchArguments":[]},{"pwStepLine":68,"gherkinStepLine":65,"keywordType":"Action","textWithKeyword":"When I click the View document button","stepMatchArguments":[]},{"pwStepLine":69,"gherkinStepLine":66,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is open","stepMatchArguments":[]},{"pwStepLine":70,"gherkinStepLine":67,"keywordType":"Action","textWithKeyword":"When I dismiss the right panel sheet via the close button","stepMatchArguments":[]},{"pwStepLine":71,"gherkinStepLine":68,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is closed","stepMatchArguments":[]}]},
  {"pwTestLine":74,"pickleLine":70,"tags":[],"steps":[{"pwStepLine":75,"gherkinStepLine":71,"keywordType":"Context","textWithKeyword":"Given my viewport is 1280 by 800","stepMatchArguments":[{"group":{"start":15,"value":"1280","children":[]},"parameterTypeName":"int"},{"group":{"start":23,"value":"800","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":76,"gherkinStepLine":72,"keywordType":"Context","textWithKeyword":"And a stubbed backend with the JKHY 2009 page-28-3 document seeded","stepMatchArguments":[]},{"pwStepLine":77,"gherkinStepLine":73,"keywordType":"Context","textWithKeyword":"And I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":78,"gherkinStepLine":74,"keywordType":"Outcome","textWithKeyword":"Then the View document button is hidden","stepMatchArguments":[]}]},
  {"pwTestLine":81,"pickleLine":76,"tags":[],"steps":[{"pwStepLine":82,"gherkinStepLine":77,"keywordType":"Context","textWithKeyword":"Given my viewport is 600 by 900","stepMatchArguments":[{"group":{"start":15,"value":"600","children":[]},"parameterTypeName":"int"},{"group":{"start":22,"value":"900","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":83,"gherkinStepLine":78,"keywordType":"Context","textWithKeyword":"And I open the empty app","stepMatchArguments":[]},{"pwStepLine":84,"gherkinStepLine":79,"keywordType":"Action","textWithKeyword":"When I open the sidebar drawer","stepMatchArguments":[]},{"pwStepLine":85,"gherkinStepLine":80,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is open","stepMatchArguments":[]},{"pwStepLine":86,"gherkinStepLine":81,"keywordType":"Outcome","textWithKeyword":"And the sidebar drawer has role dialog and aria-modal true","stepMatchArguments":[]},{"pwStepLine":87,"gherkinStepLine":82,"keywordType":"Action","textWithKeyword":"When I press Escape","stepMatchArguments":[]},{"pwStepLine":88,"gherkinStepLine":83,"keywordType":"Outcome","textWithKeyword":"Then the sidebar drawer is closed","stepMatchArguments":[]},{"pwStepLine":89,"gherkinStepLine":84,"keywordType":"Outcome","textWithKeyword":"And the hamburger button has focus","stepMatchArguments":[]}]},
  {"pwTestLine":92,"pickleLine":86,"tags":[],"steps":[{"pwStepLine":93,"gherkinStepLine":87,"keywordType":"Context","textWithKeyword":"Given my viewport is 600 by 900","stepMatchArguments":[{"group":{"start":15,"value":"600","children":[]},"parameterTypeName":"int"},{"group":{"start":22,"value":"900","children":[]},"parameterTypeName":"int"}]},{"pwStepLine":94,"gherkinStepLine":88,"keywordType":"Context","textWithKeyword":"And a stubbed backend with the JKHY 2009 page-28-3 document seeded","stepMatchArguments":[]},{"pwStepLine":95,"gherkinStepLine":89,"keywordType":"Context","textWithKeyword":"And I open the app with the JKHY 2009 page-28-3 document pinned","stepMatchArguments":[]},{"pwStepLine":96,"gherkinStepLine":90,"keywordType":"Action","textWithKeyword":"When I click the View document button","stepMatchArguments":[]},{"pwStepLine":97,"gherkinStepLine":91,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is open","stepMatchArguments":[]},{"pwStepLine":98,"gherkinStepLine":92,"keywordType":"Outcome","textWithKeyword":"And the right panel sheet has role dialog and aria-modal true","stepMatchArguments":[]},{"pwStepLine":99,"gherkinStepLine":93,"keywordType":"Action","textWithKeyword":"When I press Escape","stepMatchArguments":[]},{"pwStepLine":100,"gherkinStepLine":94,"keywordType":"Outcome","textWithKeyword":"Then the right panel sheet is closed","stepMatchArguments":[]},{"pwStepLine":101,"gherkinStepLine":95,"keywordType":"Outcome","textWithKeyword":"And the View document button has focus","stepMatchArguments":[]}]},
]; // bdd-data-end