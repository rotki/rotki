import type { FixtureManualBalance } from '../../pages/types';
import { expect, test } from '@playwright/test';
import manualBalancesFixture from '../../fixtures/account-balances/manual-balances.json' with { type: 'json' };
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { BALANCE_PRECISION } from '../../helpers/constants';
import { DashboardPage } from '../../pages/dashboard-page';
import { ManualBalancesPage } from '../../pages/manual-balances-page';

test.describe.serial('balances', () => {
  let ctx: SharedTestContext;
  const manualBalances: FixtureManualBalance[] = manualBalancesFixture;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add manual balances', async () => {
    const manualBalancesPage = new ManualBalancesPage(ctx.sharedPage);

    await manualBalancesPage.visit();

    for (let i = 0; i < 3; i++) {
      await manualBalancesPage.openAddDialog();
      const balance = manualBalances[i];
      await manualBalancesPage.addBalance(balance);
      await manualBalancesPage.visibleEntries(i + 1);
      await manualBalancesPage.isVisible(i, balance);
    }
  });

  test('data is reflected in dashboard', async () => {
    const manualBalancesPage = new ManualBalancesPage(ctx.sharedPage);
    const dashboardPage = new DashboardPage(ctx.sharedPage);

    await manualBalancesPage.visit();
    await waitForNoRunningTasks(ctx.sharedPage);

    const { total, balances } = await manualBalancesPage.getTotals();
    await dashboardPage.visit();
    const overallBalance = await dashboardPage.getOverallBalance();

    expect(overallBalance.toNumber()).toBeGreaterThanOrEqual(total.minus(BALANCE_PRECISION).toNumber());
    expect(overallBalance.toNumber()).toBeLessThanOrEqual(total.plus(BALANCE_PRECISION).toNumber());

    const dashboardBalances = await dashboardPage.getLocationBalances();

    expect(balances.map(x => x.location).sort()).toEqual(Array.from(dashboardBalances.keys()).sort());

    for (const { location, value } of balances) {
      const dashboardBalance = dashboardBalances.get(location);
      expect(dashboardBalance).toBeDefined();
      expect(dashboardBalance?.toNumber()).toBeGreaterThanOrEqual(value.minus(BALANCE_PRECISION).toNumber());
      expect(dashboardBalance?.toNumber()).toBeLessThanOrEqual(value.plus(BALANCE_PRECISION).toNumber());
    }
  });

  test('test privacy mode is off', async () => {
    const dashboardPage = new DashboardPage(ctx.sharedPage);

    await dashboardPage.visit();
    await dashboardPage.amountDisplayIsNotBlurred();
    await dashboardPage.percentageDisplayIsNotBlurred();
  });

  test('test privacy mode is semi private', async () => {
    const dashboardPage = new DashboardPage(ctx.sharedPage);

    await dashboardPage.visit();
    await ctx.app.changePrivacyMode(1);
    await dashboardPage.amountDisplayIsBlurred();
    await dashboardPage.percentageDisplayIsNotBlurred();
    await ctx.app.changePrivacyMode(0);
  });

  test('test privacy mode is private', async () => {
    const dashboardPage = new DashboardPage(ctx.sharedPage);

    await dashboardPage.visit();
    await ctx.app.changePrivacyMode(2);
    await dashboardPage.amountDisplayIsBlurred();
    await dashboardPage.percentageDisplayIsBlurred();
    await ctx.app.changePrivacyMode(0);
  });

  test('test scramble mode from top nav', async () => {
    const manualBalancesPage = new ManualBalancesPage(ctx.sharedPage);

    await manualBalancesPage.visit();
    await ctx.app.togglePrivacyMenu(true);
    await manualBalancesPage.balanceShouldMatch(manualBalances);

    await ctx.app.toggleScrambler(true);
    await manualBalancesPage.balanceShouldNotMatch(manualBalances);

    await ctx.app.toggleScrambler(false);
    await manualBalancesPage.balanceShouldMatch(manualBalances);

    await ctx.app.changeScrambleValue('0.5');
    await manualBalancesPage.balanceShouldNotMatch(manualBalances);

    await ctx.app.toggleScrambler(false);
    await manualBalancesPage.balanceShouldMatch(manualBalances);

    await ctx.app.changeRandomScrambleValue();
    await manualBalancesPage.balanceShouldNotMatch(manualBalances);

    await ctx.app.toggleScrambler(false);
    await manualBalancesPage.balanceShouldMatch(manualBalances);
    await ctx.app.togglePrivacyMenu();
  });

  test('edit and add', async () => {
    const manualBalancesPage = new ManualBalancesPage(ctx.sharedPage);

    const firstNewAmount = '200';
    await manualBalancesPage.visit();
    await manualBalancesPage.editBalance(1, firstNewAmount);
    await manualBalancesPage.visibleEntries(3);
    await manualBalancesPage.isVisible(1, {
      ...manualBalances[1],
      amount: firstNewAmount,
    });

    const secondNewAmount = '300';
    await manualBalancesPage.visit();
    await manualBalancesPage.editBalance(1, secondNewAmount);
    await manualBalancesPage.visibleEntries(3);
    await manualBalancesPage.isVisible(1, {
      ...manualBalances[1],
      amount: secondNewAmount,
    });

    await manualBalancesPage.openAddDialog();
    const apiManualBalance = { ...manualBalances[1], label: 'extra' };
    await manualBalancesPage.addBalance(apiManualBalance);
    await manualBalancesPage.visibleEntries(4);
    await manualBalancesPage.isVisible(2, apiManualBalance);
  });

  test('change currency', async () => {
    const manualBalancesPage = new ManualBalancesPage(ctx.sharedPage);

    await manualBalancesPage.visit();
    await ctx.app.changeCurrency('EUR');
    await manualBalancesPage.showsCurrency('EUR');
  });

  test('delete', async () => {
    const manualBalancesPage = new ManualBalancesPage(ctx.sharedPage);

    await manualBalancesPage.visit();
    await manualBalancesPage.deleteBalance(1);
    await manualBalancesPage.visibleEntries(3);
    await manualBalancesPage.isVisible(0, manualBalances[0]);
  });
});
