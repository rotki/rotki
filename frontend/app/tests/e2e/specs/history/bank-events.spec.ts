import { expect, type Locator, type Request } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { apiAddBankEvent } from '../../helpers/banks-api';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { selectAsset } from '../../helpers/utils';
import { EVENT_ROW } from '../../pages/history-event-rows';
import { HistoryEventsPage } from '../../pages/history-events-page';

const CONNECTION = 'rotki Solutions GmbH';

const EXTRA_DATA = {
  bank_account_id: 'account-1',
  counterparty_account: 'DE89370400440532013000',
  kind: 'transfer',
  reference: 'INV-1044',
};

function isEventWrite(request: Request, method: 'PATCH' | 'PUT'): boolean {
  return request.method() === method && new URL(request.url()).pathname.endsWith('/api/1/history/events');
}

test.describe.serial('bank transaction events', () => {
  let ctx: SharedTestContext;
  let historyPage: HistoryEventsPage;

  const bankGroup = (): Locator =>
    ctx.sharedPage.locator('[data-testid=history-event-group]').filter({ hasText: 'Qonto bank transaction' });

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    await apiAddBankEvent(ctx.sharedRequest, {
      amount: '76.69',
      asset: 'EUR',
      connectionName: CONNECTION,
      eventSubtype: 'none',
      eventType: 'receive',
      extraData: EXTRA_DATA,
      groupIdentifier: 'qonto-transaction-1',
      notes: 'Receive 76.69 EUR from PayPal',
      timestamp: 1757595000000,
    });
    historyPage = new HistoryEventsPage(ctx.sharedPage);
    await historyPage.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('should render a bank transaction under its bank header', async () => {
    await expect(bankGroup()).toHaveCount(1, { timeout: TIMEOUT_MEDIUM });
  });

  test('should keep the bank entry type and extra data when an edited bank transaction is saved', async () => {
    const row = historyPage.rows.byId(await historyPage.rows.idOfFirst(EVENT_ROW));
    const saved = ctx.sharedPage.waitForRequest(request => isEventWrite(request, 'PATCH'));

    await historyPage.rows.edit(row);
    await ctx.sharedPage.locator('[data-testid=notes] textarea:not([aria-hidden])').fill('Edited bank transaction');
    await historyPage.saveForm();

    expect((await saved).postDataJSON()).toMatchObject({
      entry_type: 'bank transaction event',
      extra_data: EXTRA_DATA,
      user_notes: 'Edited bank transaction',
    });
  });

  test('should add an event to a bank transaction group as a bank transaction', async () => {
    test.fail(true, 'onlineHistoryStateFromGroup defaults the entry type to history event, so the add is sent as a plain event');

    const added = ctx.sharedPage.waitForRequest(request => isEventWrite(request, 'PUT'));

    await bankGroup().locator('[data-testid=event-actions-menu]').click();
    await ctx.sharedPage.locator('[data-testid=event-add]').click();
    await ctx.sharedPage.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });
    await historyPage.selectAction('spend', 'fee');
    await selectAsset(ctx.sharedPage, '[data-testid=asset]', 'EUR');
    await ctx.sharedPage.locator('[data-testid=amount] input').fill('1');
    await historyPage.saveForm();

    expect((await added).postDataJSON()).toMatchObject({ entry_type: 'bank transaction event' });
  });
});
