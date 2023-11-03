import { AccountingSettingsPage } from '../../../pages/accounting-settings-page';
import { RotkiApp } from '../../../pages/rotki-app';
import { createUser } from '../../../utils/user';

describe('settings::accounting', () => {
  let username: string;
  let app: RotkiApp;
  let pageAccounting: AccountingSettingsPage;

  before(() => {
    username = createUser();
    app = new RotkiApp();
    pageAccounting = new AccountingSettingsPage();
    app.fasterLogin(username);
    pageAccounting.visit();
  });

  it('change crypto2crypto switch & validate UI message', () => {
    pageAccounting.changeSwitch('.accounting-settings__crypto2crypto', false);
  });

  it('change gas costs switch & validate UI message', () => {
    pageAccounting.changeSwitch(
      '.accounting-settings__include-gas-costs',
      false
    );
  });

  it('change tax free period value and switch & validate UI message', () => {
    pageAccounting.setTaxFreePeriodDays('50');
    pageAccounting.changeSwitch('.accounting-settings__taxfree-period', false);
  });

  it('verify changes persist', () => {
    app.fasterLogout();
    app.login(username);

    pageAccounting.visit();
    pageAccounting.verifySwitchState(
      '.accounting-settings__crypto2crypto',
      false
    );
    pageAccounting.verifySwitchState(
      '.accounting-settings__include-gas-costs',
      false
    );
    pageAccounting.verifySwitchState(
      '.accounting-settings__taxfree-period',
      false
    );
  });
});
