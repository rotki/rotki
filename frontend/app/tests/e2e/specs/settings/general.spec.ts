import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { confirmInlineSuccess } from '../../helpers/utils';
import { GeneralSettingsPage } from '../../pages/general-settings-page';

test.describe.serial('settings::general', () => {
  let ctx: SharedTestContext;
  let pageGeneral: GeneralSettingsPage;

  const settings = {
    floatingPrecision: '4',
    anonymousUsageStatistics: false,
    currency: 'JPY',
    balanceSaveFrequency: '48',
    dateDisplayFormat: '%d-%m-%Y %H:%M:%S %z',
    thousandSeparator: ',',
    decimalSeparator: '.',
    currencyLocation: 'after' as const,
  };

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);

    // Navigate to general settings once
    pageGeneral = new GeneralSettingsPage(ctx.sharedPage);
    await pageGeneral.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('change precision & validate UI message', async () => {
    await pageGeneral.setFloatingPrecision(settings.floatingPrecision);
    await confirmInlineSuccess(
      ctx.sharedPage,
      '[data-cy=floating-precision-settings] .details .text-rui-success',
      settings.floatingPrecision,
    );
  });

  test('change anonymous statistics switch & validate UI message', async () => {
    await pageGeneral.changeAnonymousUsageStatistics();
  });

  test('change main currency and validate UI message', async () => {
    await pageGeneral.selectCurrency(settings.currency);
    await confirmInlineSuccess(ctx.sharedPage, '[data-cy=currency-selector]', settings.currency);
  });

  test('change balance save frequency and validate UI message', async () => {
    await pageGeneral.setBalanceSaveFrequency(settings.balanceSaveFrequency);
    await confirmInlineSuccess(
      ctx.sharedPage,
      '[data-cy=balance-save-frequency-input] .details',
      settings.balanceSaveFrequency,
    );
  });

  test('change date display format and validate UI message', async () => {
    await pageGeneral.setDateDisplayFormat(settings.dateDisplayFormat);
    await confirmInlineSuccess(
      ctx.sharedPage,
      '[data-cy=date-display-format-input] .details',
      settings.dateDisplayFormat,
    );
  });

  test('verify changed settings', async () => {
    await pageGeneral.navigateAway();
    await pageGeneral.visit();
    await pageGeneral.verify(settings);
  });

  test('verify settings persist after re-login', async () => {
    await ctx.app.relogin(ctx.username);
    await pageGeneral.visit();
    await pageGeneral.verify(settings);
  });
});
