import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { HistoricPricePage, LatestPricePage, OraclePricePage } from '../../pages/price-manager-page';

test.describe('price manager', () => {
  test.describe.serial('latest', () => {
    let ctx: SharedTestContext;
    let page: LatestPricePage;

    test.beforeAll(async ({ browser, request }) => {
      ctx = await createLoggedInContext(browser, request, { disableModules: true });
      page = new LatestPricePage(ctx.sharedPage);
      await page.visit();
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('creates a latest price', async () => {
      await page.addPrice('EUR', 'USD', '1234');
      await page.expectRowWithValue('1,234');
    });

    test('edits the price value', async () => {
      await page.editPrice('1,234', '5678');
      await page.expectRowWithValue('5,678');
    });

    test('deletes the price', async () => {
      await page.deletePrice('5,678');
    });

    test('shows validation errors when required fields are empty', async () => {
      await page.openAddDialog();
      await page.submitDialog();
      await page.expectRequiredErrors();
      await page.cancelDialog();
    });

    test('filters table by from-asset', async () => {
      await page.addPrice('EUR', 'USD', '999');
      await page.expectRowWithValue('999');

      await page.filterByFromAsset('BTC');
      await page.expectVisibleRowCount(0);

      await page.filterByFromAsset('EUR');
      await page.expectRowWithValue('999');

      await page.deletePrice('999');
    });
  });

  test.describe.serial('historic', () => {
    let ctx: SharedTestContext;
    let page: HistoricPricePage;

    test.beforeAll(async ({ browser, request }) => {
      ctx = await createLoggedInContext(browser, request, { disableModules: true });
      page = new HistoricPricePage(ctx.sharedPage);
      await page.visit();
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('creates a historic price', async () => {
      await page.addPrice('EUR', 'USD', '1500', '01/06/2024 12:00:00');
      await page.expectRowWithValue('1,500');
    });

    test('edits the historic price value', async () => {
      await page.editPrice('1,500', '1750');
      await page.expectRowWithValue('1,750');
    });

    test('deletes the historic price', async () => {
      await page.deletePrice('1,750');
    });

    test('shows validation errors when required fields are empty', async () => {
      await page.openAddDialog();
      await page.submitDialog();
      await page.expectRequiredErrors();
      await page.cancelDialog();
    });

    test('filters table by from-asset', async () => {
      await page.addPrice('EUR', 'USD', '888', '01/06/2024 12:00:00');
      await page.expectRowWithValue('888');

      await page.filterByFromAsset('BTC');
      await page.expectVisibleRowCount(0);

      await page.filterByFromAsset('EUR');
      await page.expectRowWithValue('888');

      await page.deletePrice('888');
    });
  });

  test.describe.serial('oracle', () => {
    let ctx: SharedTestContext;
    let page: OraclePricePage;

    test.beforeAll(async ({ browser, request }) => {
      ctx = await createLoggedInContext(browser, request, { disableModules: true });
      page = new OraclePricePage(ctx.sharedPage);
      await page.visit();
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('renders the oracle prices table', async () => {
      await page.expectTableVisible();
    });
  });
});
