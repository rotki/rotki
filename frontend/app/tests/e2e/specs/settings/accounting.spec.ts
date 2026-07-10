import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { AccountingSettingsPage } from '../../pages/accounting-settings-page';

test.describe.serial('settings::accounting', () => {
  let ctx: SharedTestContext;
  let pageAccounting: AccountingSettingsPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);

    // Navigate to accounting settings once
    pageAccounting = new AccountingSettingsPage(ctx.sharedPage);
    await pageAccounting.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('change crypto2crypto switch & validate UI message', async () => {
    await pageAccounting.changeSwitch('[data-testid=crypto2crypto-switch]', false);
  });

  test('change gas costs switch & validate UI message', async () => {
    await pageAccounting.changeSwitch('[data-testid=include-gas-costs-switch]', false);
  });

  test('change tax free period value and switch & validate UI message', async () => {
    await pageAccounting.setTaxFreePeriodDays('50');
    await pageAccounting.changeSwitch('[data-testid=taxfree-period-switch]', false);
  });

  test('change cost basis fee settings & validate UI message', async () => {
    await pageAccounting.verifySwitchState('[data-testid=include-fees-in-cost-basis-switch]', true);
    await pageAccounting.changeSwitch('[data-testid=include-fees-in-cost-basis-switch]', false);
  });

  test('verify changes persist', async () => {
    await ctx.app.relogin(ctx.username);
    await pageAccounting.visit();
    await pageAccounting.verifySwitchState('[data-testid=crypto2crypto-switch]', false);
    await pageAccounting.verifySwitchState('[data-testid=include-gas-costs-switch]', false);
    await pageAccounting.verifySwitchState('[data-testid=taxfree-period-switch]', false);
    await pageAccounting.verifySwitchState('[data-testid=include-fees-in-cost-basis-switch]', false);
  });
});
