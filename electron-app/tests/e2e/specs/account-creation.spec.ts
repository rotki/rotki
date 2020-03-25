import { Guid } from '../../common/guid';
import { RotkiApp } from '../pages/rotki-app';

describe('Accounts', () => {
  let username: string;
  let app: RotkiApp;

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
  });

  it('create account', () => {
    app.visit();
    app.createAccount(username);
    app.closePremiumOverlay();
    app.logout();
  });

  it('login', () => {
    app.login(username);
    app.closePremiumOverlay();
    app.logout();
  });
});
