import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { AirdropsPage } from '../../pages/airdrops-page';

test.describe.serial('airdrops', () => {
  let ctx: SharedTestContext;
  let page: AirdropsPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new AirdropsPage(ctx.sharedPage);
    await page.setupMocks();
    await page.visit();
    await page.waitForLoaded();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('lists every airdrop source', async () => {
    await page.expectRowCount(5);
    for (const source of ['uniswap', 'gitcoin', 'shapeshift', 'badger', 'poap'])
      await page.expectRowVisible(source);
  });

  test('filters to claimed airdrops', async () => {
    await page.selectStatus('Claimed');
    await page.expectRowCount(1);
    await page.expectRowVisible('uniswap');
    await page.expectRowMissing('shapeshift');
  });

  test('filters to unclaimed airdrops', async () => {
    await page.selectStatus('Unclaimed');
    await page.expectRowVisible('gitcoin');
    await page.expectRowVisible('badger');
    await page.expectRowMissing('uniswap');
  });

  test('filters to missed airdrops', async () => {
    await page.selectStatus('Missed');
    await page.expectRowCount(1);
    await page.expectRowVisible('badger');
    await page.expectRowMissing('gitcoin');
  });

  test('shows the info alert for the unknown filter', async () => {
    await page.selectStatus('Unknown');
    await page.expectUnknownAlertVisible();
    await page.expectRowVisible('shapeshift');
  });

  test('refresh re-queries the airdrops', async () => {
    await page.selectStatus('All');
    await page.expectRowCount(5);
    const before = page.triggerCount;
    await page.refresh();
    await expect.poll(() => page.triggerCount).toBeGreaterThan(before);
    await page.waitForLoaded();
    await page.expectRowCount(5);
  });

  // Kept last: expanding the POAP row injects a nested detail table whose rows
  // would otherwise inflate the main row count for any following test.
  test('expands POAP delivery details', async () => {
    await page.expandPoapRow();
    await page.expectPoapDetail('YFI OG');
  });
});
