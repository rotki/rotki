import { Guid } from '../../common/guid';
import { AccountingSettingsPage } from '../pages/accounting-settings-page';
import { GeneralSettingsPage } from '../pages/general-settings-page';
import { RotkiApp } from '../pages/rotki-app';
import { UserSecuritySettingsPage } from '../pages/user-security-settings-page';

describe('settings', () => {
  let username: string;
  let password: string;
  let newPassword: string;
  let app: RotkiApp;
  let pageGeneral: GeneralSettingsPage;
  let pageAccounting: AccountingSettingsPage;
  let pageUserSecurity: UserSecuritySettingsPage;

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
    password = '1234';
    newPassword = '5678';
    app = new RotkiApp();
    pageGeneral = new GeneralSettingsPage();
    pageUserSecurity = new UserSecuritySettingsPage();
    pageAccounting = new AccountingSettingsPage();
    app.fasterLogin(username);
  });

  after(() => {
    app.fasterLogout();
  });

  describe('General Settings', () => {
    const name = 'local';
    const endpoint = 'http://localhost:9001';

    before(() => {
      pageGeneral.visit();
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
  });

  describe('Accounting Settings', () => {
    before(() => {
      pageAccounting.visit();
    });

    describe('trade settings', () => {
      it('change crypto2crypto switch & validate UI message', () => {
        pageAccounting.changeSwitch('.accounting-settings__crypto2crypto');
      });
      it('change gas costs switch & validate UI message', () => {
        pageAccounting.changeSwitch('.accounting-settings__include-gas-costs');
      });
      it('change tax free period value and switch & validate UI message', () => {
        pageAccounting.setTaxFreePeriodDays('50');
        pageAccounting.changeSwitch('.accounting-settings__taxfree-period');
      });
    });
  });

  describe('Data & Security Settings', () => {
    it('change user password', () => {
      pageUserSecurity.visit();
      pageUserSecurity.changePassword(password, newPassword);
      pageUserSecurity.confirmSuccess();
    });
  });

  describe('Verify settings persist after re-login', () => {
    it('Log in with new password', () => {
      app.fasterLogout();
      // If we don't visit the logout doesn't persist the skip_update parameter
      app.visit();
      app.login(username, newPassword);
      app.closePremiumOverlay();
    });

    it('General settings', () => {
      pageGeneral.visit();
      pageGeneral.verify(settings);
    });

    it('Accounting settings', () => {
      pageAccounting.visit();
      pageAccounting.verifySwitchState(
        '.accounting-settings__crypto2crypto',
        'false'
      );
      pageAccounting.verifySwitchState(
        '.accounting-settings__include-gas-costs',
        'false'
      );
      pageAccounting.verifySwitchState(
        '.accounting-settings__taxfree-period',
        'false'
      );
    });
  });
});
