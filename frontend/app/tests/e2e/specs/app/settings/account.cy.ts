import { AccountSettingsPage } from '../../../pages/account-settings-page';
import { RotkiApp } from '../../../pages/rotki-app';
import { createUser } from '../../../utils/user';

describe('settings::data & security', () => {
  let username: string;
  let password: string;
  let newPassword: string;
  let app: RotkiApp;
  let pageUserSecurity: AccountSettingsPage;

  before(() => {
    username = createUser();
    password = '1234';
    newPassword = '5678';
    app = new RotkiApp();
    pageUserSecurity = new AccountSettingsPage();
    app.fasterLogin(username);
  });

  it('change user password', () => {
    pageUserSecurity.visit();
    pageUserSecurity.changePassword(password, newPassword);
    pageUserSecurity.confirmSuccess();
  });

  it('verify that new password works', () => {
    app.relogin(username, newPassword);
  });
});
