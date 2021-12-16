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
    app.visit();
    app.createAccount(username, password);
  });

  after(() => {
    app.logout();
  });

  describe('General Settings', () => {
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

    it('change general settings', () => {
      // pageGeneral.confirmSuccess();
    });

    it('verify changed settings', () => {
      pageGeneral.navigateAway();
      pageGeneral.visit();
      pageGeneral.verify(settings);
    });

    it('change rpc without success', () => {
      pageGeneral.setRpcEndpoint('http://localhost:9001');
      pageGeneral.confirmInlineFailure(
        '.general-settings__fields__rpc-endpoint',
        'http://localhost:9001'
      );
    });

    it('verify changed settings', () => {
      pageGeneral.navigateAway();
      pageGeneral.visit();
      pageGeneral.verify(settings);
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

    describe('ignored asset settings', () => {
      it('add an ignored asset and validate UI message it has been added', () => {
        pageAccounting.addIgnoredAsset('1SG');
        pageAccounting.confirmInlineSuccess(
          '.accounting-settings__asset-to-ignore',
          '1SG'
        );
      });
      it('add another 2 ignored assets and confirm count is 3', () => {
        pageAccounting.addIgnoredAsset('ZIX');
        pageAccounting.confirmInlineSuccess(
          '.accounting-settings__asset-to-ignore',
          'ZIX'
        );
        pageAccounting.addIgnoredAsset('1CR');
        pageAccounting.confirmInlineSuccess(
          '.accounting-settings__asset-to-ignore',
          '1CR'
        );
        pageAccounting.ignoredAssetCount('3');
      });
      it('cannot add already ignored asset & validate UI message', () => {
        pageAccounting.addIgnoredAsset('1SG');
        pageAccounting.confirmInlineFailure(
          '.accounting-settings__asset-to-ignore',
          '1SG'
        );
      });
      it('remove an ignored asset, validate UI message, and confirm count is 2', () => {
        pageAccounting.remIgnoredAsset('1SG');
        pageAccounting.confirmInlineSuccess(
          '.accounting-settings__ignored-assets',
          '1SG'
        );
        pageAccounting.ignoredAssetCount('2');
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
      app.logout();
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
      pageAccounting.ignoredAssetCount('2');
    });
  });
});
