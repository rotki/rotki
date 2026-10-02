import { expect, type Locator, type Page, type Route } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { HistoryEventsPage } from '../../pages/history-events-page';

/**
 * The conflicts table has to scroll inside its own region, in the dialog and in the pinned rail,
 * with the surrounding chrome left in place. The backend only records conflicts when decoding hits
 * them, so the endpoint is mocked with more rows than either container can show at once.
 */
const CONFLICT_COUNT = 40;

const CONFLICTS = Array.from({ length: CONFLICT_COUNT }, (_, i) => ({
  action: 'repull',
  chain: 'ethereum',
  group_identifier: null,
  last_error: null,
  last_retry_ts: null,
  redecode_reason: null,
  repull_reason: 'all_zero_gas',
  timestamp: 1700000000 + i * 3600,
  tx_hash: `0x${(i + 1).toString(16).padStart(64, '0')}`,
}));

async function fulfillConflicts(route: Route): Promise<void> {
  const request = route.request();
  let result: unknown;
  if (request.method() === 'POST') {
    result = { failed: 0, pending: CONFLICT_COUNT };
  }
  else {
    const params = new URL(request.url()).searchParams;
    const limit = Number(params.get('limit') ?? 10);
    const offset = Number(params.get('offset') ?? 0);
    result = {
      entries: CONFLICTS.slice(offset, offset + limit),
      entries_found: CONFLICT_COUNT,
      entries_limit: -1,
      entries_total: CONFLICT_COUNT,
    };
  }
  await route.fulfill({
    body: JSON.stringify({ message: '', result }),
    contentType: 'application/json',
    status: 200,
  });
}

async function scrollToEnd(region: Locator): Promise<void> {
  await region.evaluate((el) => {
    el.style.scrollBehavior = 'auto';
    el.scrollTop = el.scrollHeight;
  });
}

async function expectScrollsInside(page: Page, container: Locator): Promise<void> {
  const region = container.locator('[data-testid=scrollable-dialog-body]');
  await expect(region.locator('tbody tr')).toHaveCount(10, { timeout: TIMEOUT_MEDIUM });

  const { clientHeight, scrollHeight } = await region.evaluate(el => ({
    clientHeight: el.clientHeight,
    scrollHeight: el.scrollHeight,
  }));
  expect(scrollHeight, 'the table region is bounded and overflows').toBeGreaterThan(clientHeight);

  await scrollToEnd(region);
  await expect(region.locator('tbody tr').last()).toBeInViewport({ ratio: 1 });
  expect(await page.evaluate(() => document.scrollingElement?.scrollTop ?? 0)).toBe(0);
}

test.describe.serial('internal transaction conflicts scrolling', () => {
  let ctx: SharedTestContext;
  let page: Page;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = ctx.sharedPage;
    await page.setViewportSize({ height: 720, width: 1280 });
    await page.route(/\/blockchains\/transactions\/internal\/conflicts(\?|$)/, fulfillConflicts);
    await new HistoryEventsPage(page).visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('scrolls the table inside the dialog and keeps its footer visible', async () => {
    await page.locator('[data-testid=actions-center-button]').first().click();
    await page.locator('[data-testid=actions-center-rescan]').click();
    const row = page.locator('[data-testid=actions-center-row][data-key=internal-conflicts]');
    await row.locator('[data-testid=actions-center-row-action]').click();

    const dialog = page.locator('[data-testid=internal-tx-conflicts-dialog]');
    await expect(dialog).toBeVisible();
    await expectScrollsInside(page, dialog);
    await expect(dialog.locator('[data-testid=internal-tx-conflicts-dialog-close]')).toBeInViewport({ ratio: 1 });
  });

  test('scrolls the table inside the pinned panel', async () => {
    await page.locator('[data-testid=internal-tx-conflicts-pin]').click();
    await expect(page.locator('[data-testid=internal-tx-conflicts-dialog]')).toHaveCount(0);

    await expectScrollsInside(page, page.locator('[data-testid=pinned-panel-body]'));
  });
});
