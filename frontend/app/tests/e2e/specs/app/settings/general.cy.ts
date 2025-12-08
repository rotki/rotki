import { GeneralSettingsPage } from '../../../pages/general-settings-page';
import { RotkiApp } from '../../../pages/rotki-app';
import { createUser } from '../../../utils/user';

describe('settings::general', () => {
  let username: string;
  let app: RotkiApp;
  let pageGeneral: GeneralSettingsPage;

  const settings = {
    floatingPrecision: '4',
    anonymousUsageStatistics: false,
    currency: 'JPY',
    balanceSaveFrequency: '48',
    dateDisplayFormat: '%d-%m-%Y %H:%M:%S %z',
    thousandSeparator: ',',
    decimalSeparator: '.',
    currencyLocation: 'after' as 'after' | 'before',
    btcMempoolApi: '',
  };

  before(() => {
    username = createUser();
    app = new RotkiApp();
    pageGeneral = new GeneralSettingsPage();
    app.fasterLogin(username);
    pageGeneral.visit();
  });

  it('change precision & validate UI message', () => {
    pageGeneral.setFloatingPrecision(settings.floatingPrecision);
    pageGeneral.confirmInlineSuccess(
      '[data-cy=floating-precision-settings] .details .text-rui-success',
      settings.floatingPrecision,
    );
  });

  it('change anonymous statistics switch & validate UI message', () => {
    pageGeneral.changeAnonymousUsageStatistics();
  });

  it('change main currency and validate UI message', () => {
    pageGeneral.selectCurrency(settings.currency);
    pageGeneral.confirmInlineSuccess('[data-cy=currency-selector]', settings.currency);
  });

  it('change balance save frequency and validate UI message', () => {
    pageGeneral.setBalanceSaveFrequency(settings.balanceSaveFrequency);
    pageGeneral.confirmInlineSuccess(
      '[data-cy=balance-save-frequency-input] .details',
      settings.balanceSaveFrequency,
    );
  });

  it('change date display format and validate UI message', () => {
    pageGeneral.setDateDisplayFormat(settings.dateDisplayFormat);
    pageGeneral.confirmInlineSuccess(
      '[data-cy=date-display-format-input] .details',
      settings.dateDisplayFormat,
    );
  });

  it('verify changed settings', () => {
    pageGeneral.navigateAway();
    pageGeneral.visit();
    pageGeneral.verify(settings);
  });

  it('verify settings persist after re-login', () => {
    app.relogin(username);
    pageGeneral.visit();
    pageGeneral.verify(settings);
  });
});
