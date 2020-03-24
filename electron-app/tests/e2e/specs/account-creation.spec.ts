import { Guid } from '../../common/guid';
import { RotkiApp } from '../pages/rotki-app';

describe('Accounts', () => {
  let username: string;
  let loginPage: RotkiApp;

  before(() => {
    username = Guid.newGuid().toString();
    loginPage = new RotkiApp();
  });

  it('create account', () => {
    loginPage.visit();
    loginPage.createAccount(username);
    loginPage.closePremiumOverlay();
    loginPage.logout();
  });

  it('login', () => {
    loginPage.login(username);
    loginPage.closePremiumOverlay();
    loginPage.logout();
  });
});
