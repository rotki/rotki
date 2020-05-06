import { Guid } from '../../common/guid';
import { GeneralSettingsPage } from '../pages/general-settings-page';
import { RotkiApp } from '../pages/rotki-app';

describe('General Settings', () => {
  let username: string;
  let password: string;
  let newPassword: string;
  let app: RotkiApp;
  let page: GeneralSettingsPage;

  const settings = {
    floatingPrecision: '4',
    anonymizedLogs: true,
    anonymousUsageStatistics: false,
    historicDataStart: '03/10/2018',
    currency: 'JPY',
    balanceSaveFrequency: '48',
    dateDisplayFormat: '%d-%m-%Y %H:%M:%S %z',
    rpcEndpoint: 'http://localhost:8545'
  };

  before(() => {
    username = Guid.newGuid().toString();
    password = '1234';
    newPassword = '5678';
    app = new RotkiApp();
    page = new GeneralSettingsPage();
    app.visit();
    app.createAccount(username, password);
    app.closePremiumOverlay();
  });

  after(() => {
    app.logout();
  });

  it('change general settings', () => {
    page.visit();
    page.setFloatingPrecision(settings.floatingPrecision);
    page.changeAnonymizedLogs();
    page.changeAnonymousUsageStatistics();
    page.setHistoryDataStart(settings.historicDataStart);
    page.selectCurrency(settings.currency);
    page.setBalanceSaveFrequency(settings.balanceSaveFrequency);
    page.setDateDisplayFormat(settings.dateDisplayFormat);
    page.saveSettings();
    page.confirmSuccess();
  });

  it('verify changed settings', () => {
    page.navigateAway();
    page.visit();
    page.verify(settings);
  });

  it('change user password and revert', () => {
    page.visit();
    page.changePassword(password, newPassword);
    page.confirmSuccess();
  });

  it('change rpc without success', () => {
    page.setRpcEndpoint('http://localhost:9001');
    page.saveSettings();
    page.confirmFailure();
  });

  it('verify settings persist re-login', () => {
    app.logout();
    app.login(username, newPassword);
    app.closePremiumOverlay();
    page.visit();
    page.verify(settings);
  });
});
