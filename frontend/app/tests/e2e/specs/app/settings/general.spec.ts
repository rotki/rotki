import { Guid } from '../../../common/guid';
import { GeneralSettingsPage } from '../../../pages/general-settings-page';
import { RotkiApp } from '../../../pages/rotki-app';

describe('settings::general', () => {
  let username: string;
  let app: RotkiApp;
  let pageGeneral: GeneralSettingsPage;

  const name = 'local';
  const endpoint = 'http://localhost:9001';

  const settings = {
    floatingPrecision: '4',
    anonymousUsageStatistics: false,
    currency: 'JPY',
    balanceSaveFrequency: '48',
    dateDisplayFormat: '%d-%m-%Y %H:%M:%S %z',
    thousandSeparator: ',',
    decimalSeparator: '.',
    currencyLocation: 'after' as 'after' | 'before',
    rpcEndpoint: 'http://localhost:8545'
  };

  before(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    pageGeneral = new GeneralSettingsPage();
    app.fasterLogin(username);
    pageGeneral.visit();
  });

  after(() => {
    app.fasterLogout();
  });

  it('change precision & validate UI message', () => {
    pageGeneral.setFloatingPrecision(settings.floatingPrecision);
    pageGeneral.confirmInlineSuccess(
      '.general-settings__fields__floating-precision',
      settings.floatingPrecision
    );
  });

  it('change anonymous statistics switch & validate UI message', () => {
    pageGeneral.changeAnonymousUsageStatistics();
  });

  it('change main currency and validate UI message', () => {
    pageGeneral.selectCurrency(settings.currency);
    pageGeneral.confirmInlineSuccess(
      '.general-settings__fields__currency-selector',
      settings.currency
    );
  });

  it('change balance save frequency and validate UI message', () => {
    pageGeneral.setBalanceSaveFrequency(settings.balanceSaveFrequency);
    pageGeneral.confirmInlineSuccess(
      '.general-settings__fields__balance-save-frequency',
      settings.balanceSaveFrequency
    );
  });

  it('change date display format and validate UI message', () => {
    pageGeneral.setDateDisplayFormat(settings.dateDisplayFormat);
    pageGeneral.confirmInlineSuccess(
      '.general-settings__fields__date-display-format',
      settings.dateDisplayFormat
    );
  });

  it('verify changed settings', () => {
    pageGeneral.navigateAway();
    pageGeneral.visit();
    pageGeneral.verify(settings);
    pageGeneral.confirmRPCmissing(name, endpoint);
  });

  it('add ethereum rpc', () => {
    pageGeneral.confirmRPCmissing(name, endpoint);
    pageGeneral.addEthereumRPC(name, endpoint);
    pageGeneral.confirmRPCAddition(name, endpoint);
  });

  it('verify changed settings', () => {
    pageGeneral.navigateAway();
    pageGeneral.visit();
    pageGeneral.verify(settings);
    pageGeneral.confirmRPCAddition(name, endpoint);
  });

  it('verify settings persist after re-login', () => {
    app.fasterLogout();
    app.login(username);

    pageGeneral.visit();
    pageGeneral.verify(settings);
  });
});
