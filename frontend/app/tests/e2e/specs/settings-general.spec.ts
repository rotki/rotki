import { Guid } from '../../common/guid';
import { AccountingSettingsPage } from '../pages/accounting-settings-page';
import { GeneralSettingsPage } from '../pages/general-settings-page';
import { RotkiApp } from '../pages/rotki-app';
import { UserSecuritySettingsPage } from '../pages/user-security-settings-page';

describe('Settings', () => {
  let username: string;
  let password: string;
  let newPassword: string;
  let app: RotkiApp;
  let pageGeneral: GeneralSettingsPage;
  let pageAccounting: AccountingSettingsPage;
  let pageUserSecurity: UserSecuritySettingsPage;

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
    pageGeneral = new GeneralSettingsPage();
    pageUserSecurity = new UserSecuritySettingsPage();
    pageAccounting = new AccountingSettingsPage();
    app.visit();
    app.createAccount(username, password);
    app.closePremiumOverlay();
  });

  after(() => {
    app.logout();
  });

  describe('General Settings', () => {
    it('change general settings', () => {
      pageGeneral.visit();
      pageGeneral.setFloatingPrecision(settings.floatingPrecision);
      pageGeneral.changeAnonymizedLogs();
      pageGeneral.changeAnonymousUsageStatistics();
      pageGeneral.setHistoryDataStart(settings.historicDataStart);
      pageGeneral.selectCurrency(settings.currency);
      pageGeneral.setBalanceSaveFrequency(settings.balanceSaveFrequency);
      pageGeneral.setDateDisplayFormat(settings.dateDisplayFormat);
      pageGeneral.saveSettings();
      pageGeneral.confirmSuccess();
    });

    it('verify changed settings', () => {
      pageGeneral.navigateAway();
      pageGeneral.visit();
      pageGeneral.verify(settings);
    });

    it('change rpc without success', () => {
      pageGeneral.setRpcEndpoint('http://localhost:9001');
      pageGeneral.saveSettings();
      pageGeneral.confirmFailure();
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
        pageAccounting.changeSwitch('.settings-accounting__crypto2crypto');
      });
      it('change gas costs switch & validate UI message', () => {
        pageAccounting.changeSwitch('.settings-accounting__include-gas-costs');
      });
      it('change tax free period value and switch & validate UI message', () => {
        pageAccounting.setTaxFreePeriodDays('50');
        pageAccounting.changeSwitch('.settings-accounting__taxfree-period');
      });
    });

    describe('ignored asset settings', () => {
      it('add an ignored asset and validate UI message it has been added', () => {
        pageAccounting.addIgnoredAsset('1SG');
        pageAccounting.confirmInlineSuccess(
          '.settings-accounting__asset-to-ignore',
          '1SG'
        );
      });
      it('add another 2 ignored assets and confirm count is 3', () => {
        pageAccounting.addIgnoredAsset('ZIX');
        pageAccounting.addIgnoredAsset('1CR');
        pageAccounting.ignoredAssetCount('3');
      });
      it('cannot add already ignored asset & validate UI message', () => {
        pageAccounting.addIgnoredAsset('1SG');
        pageAccounting.confirmInlineFailure(
          '.settings-accounting__asset-to-ignore',
          '1SG'
        );
      });
      it('remove an ignored asset, validate UI message, and confirm count is 2', () => {
        pageAccounting.remIgnoredAsset('1SG');
        pageAccounting.confirmInlineSuccess(
          '.settings-accounting__ignored-assets',
          '1SG'
        );
        pageAccounting.ignoredAssetCount('2');
      });
    });
  });

  describe('User & Security Settings', () => {
    it('change user password', () => {
      pageUserSecurity.visit();
      pageUserSecurity.changePassword(password, newPassword);
      pageUserSecurity.confirmSuccess();
    });
  });

  describe('Verify settings persist after re-login', () => {
    it('Log in with new password', () => {
      app.logout();
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
        '.settings-accounting__crypto2crypto',
        'false'
      );
      pageAccounting.verifySwitchState(
        '.settings-accounting__include-gas-costs',
        'false'
      );
      pageAccounting.verifySwitchState(
        '.settings-accounting__taxfree-period',
        'false'
      );
      pageAccounting.ignoredAssetCount('2');
    });
  });
});
