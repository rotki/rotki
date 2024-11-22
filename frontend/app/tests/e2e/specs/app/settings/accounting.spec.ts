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
    pageAccounting.changeSwitch('[data-cy=crypto2crypto-switch]', false);
  });

  it('change gas costs switch & validate UI message', () => {
    pageAccounting.changeSwitch('[data-cy=include-gas-costs-switch]', false);
  });

  it('change tax free period value and switch & validate UI message', () => {
    pageAccounting.setTaxFreePeriodDays('50');
    pageAccounting.changeSwitch('[data-cy=taxfree-period-switch]', false);
  });

  it('change cost basis fee settings & validate UI message', () => {
    pageAccounting.verifySwitchState('[data-cy=include-fees-in-cost-basis-switch]', true);
    pageAccounting.changeSwitch('[data-cy=include-fees-in-cost-basis-switch]', false);
  });

  it('verify changes persist', () => {
    app.relogin(username);
    pageAccounting.visit();
    pageAccounting.verifySwitchState('[data-cy=crypto2crypto-switch]', false);
    pageAccounting.verifySwitchState('[data-cy=include-gas-costs-switch]', false);
    pageAccounting.verifySwitchState('[data-cy=taxfree-period]', false);
    pageAccounting.verifySwitchState('[data-cy=include-fees-in-cost-basis-switch]', false);
  });
});
