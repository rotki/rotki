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

  // The negative control: the same bar, one value different, and the previous set is gone. Without
  // it, a filter that quietly matched everything of one kind would still have passed above.
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
    // The deposit rules the previous test filtered out are back, which the withdrawal-only table
    // left on screen would not satisfy.
    await page.expectEventTypePresent('Deposit');
  });

  // The two tabs are one request parameter, not a client-side split: the custom tab asks for the
  // rules written for a single event each, and none of the seeded or default rules is one.
  test('switches between general and event-specific rules', async () => {
    await page.selectRuleTab('custom');
    await page.expectNoRules();

    await page.selectRuleTab('regular');
    await page.expectRules();
  });
});
