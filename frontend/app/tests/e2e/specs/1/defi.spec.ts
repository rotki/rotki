import { Guid } from '../../../common/guid';
import { DefiPage } from '../../pages/defi-page';
import { RotkiApp } from '../../pages/rotki-app';

describe('defi', () => {
  let username: string;
  let app: RotkiApp;
  let page: DefiPage;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new DefiPage();
    app.fasterLogin(username);
  });

  it('goes through the wizard', () => {
    page.visit();
    page.goToSelectModules();
    page.selectModules();
    page.selectAccounts();
    page.defiOverviewIsVisible();
  });

  after(() => {
    app.fasterLogout();
  });
});
