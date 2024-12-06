import { DefiPage } from '../../pages/defi-page';
import { RotkiApp } from '../../pages/rotki-app';
import { createUser } from '../../utils/user';

describe('defi', () => {
  let username: string;
  let app: RotkiApp;
  let page: DefiPage;

  before(() => {
    username = createUser();
    app = new RotkiApp();
    page = new DefiPage();
    app.fasterLogin(username);
  });

  it('goes through the wizard', () => {
    page.visit();
    page.goToSelectModules();
    page.selectModules();
    page.defiOverviewIsVisible();
  });
});
