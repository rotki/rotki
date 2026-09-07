import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { apiAddAccountingRules, type SeedAccountingRule } from '../../helpers/accounting';
import { AccountingSettingsPage } from '../../pages/accounting-settings-page';
import { PillFilterBar } from '../../pages/pill-filter-bar';

/**
 * One rule of each event type the filter is asserted on, so there is always something to find and
 * something to exclude.
 *
 * Seeded rather than assumed: rotki's default rules come from the data repo, not from account
 * creation, so how many rules a fresh user has at any given moment is a race. That is also why
 * nothing below counts rows — the assertions are about *which* rules a filter leaves, which holds
 * whether the defaults have landed or not.
 */
const SEEDED_RULES: SeedAccountingRule[] = [
  { eventSubtype: 'deposit asset', eventType: 'deposit' },
  { eventSubtype: 'remove asset', eventType: 'withdrawal' },
];

/** Serial: every test drives the one table, and each leaves it as it found it. */
test.describe.serial('settings::accounting-rules', () => {
  let ctx: SharedTestContext;
  let page: AccountingSettingsPage;
  let filter: PillFilterBar;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    await apiAddAccountingRules(request, SEEDED_RULES);

    page = new AccountingSettingsPage(ctx.sharedPage);
    filter = new PillFilterBar(ctx.sharedPage);
    await page.visit();
    await page.expectRules();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('leaves only the rules of the filtered event type', async () => {
    await filter.addField('eventTypes');
    await filter.selectValue('deposit', 'Deposit');
    await filter.closeEditor('eventTypes');

    await filter.expectPillVisible('eventTypes');
    await page.expectOnlyEventType('Deposit');
  });

  // The negative control: a filter matching everything of one kind would have passed above.
  test('follows the filter when the value changes', async () => {
    await filter.openPillEditor('eventTypes');
    await filter.selectValue('deposit', 'Deposit');
    await filter.selectValue('withdrawal', 'Withdrawal');
    await filter.closeEditor('eventTypes');

    await page.expectOnlyEventType('Withdrawal');
  });

  test('restores the unfiltered rules when the filter is cleared', async () => {
    await filter.clearAll();

    await filter.expectNoPill('eventTypes');
    // The deposit rules are back, which the previous test's withdrawal-only table would not show.
    await page.expectEventTypePresent('Deposit');
  });

  // The tabs are one request parameter, and no seeded or default rule is written for one event.
  test('switches between general and event-specific rules', async () => {
    await page.selectRuleTab('custom');
    await page.expectNoRules();

    await page.selectRuleTab('regular');
    await page.expectRules();
  });
});
