import { Guid } from '../../../common/guid';
import { RotkiApp } from '../../../pages/rotki-app';
import { UserSecuritySettingsPage } from '../../../pages/user-security-settings-page';

describe('settings::data & security', () => {
  let username: string;
  let password: string;
  let newPassword: string;
  let app: RotkiApp;
  let pageUserSecurity: UserSecuritySettingsPage;

  before(() => {
    username = Guid.newGuid().toString();
    password = '1234';
    newPassword = '5678';
    app = new RotkiApp();
    pageUserSecurity = new UserSecuritySettingsPage();
    app.fasterLogin(username);
  });

  after(() => {
    app.fasterLogout();
  });

  it('change user password', () => {
    pageUserSecurity.visit();
    pageUserSecurity.changePassword(password, newPassword);
    pageUserSecurity.confirmSuccess();
  });

  it('verify that new password works', () => {
    app.fasterLogout();
    app.login(username, newPassword);
    app.closePremiumOverlay();
  });
});
