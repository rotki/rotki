import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { apiEnsureSymbolsNotIgnored } from '../../helpers/api';
import { AssetsManagerPage } from '../../pages/assets-manager-page';

// Assets used in ignored asset tests
const TEST_ASSETS_TO_IGNORE = ['1SG', 'ZIX', '1CR'];

test.describe('assets', () => {
  test.describe.serial('ignored asset settings', () => {
    let ignoredAssets = 0;
    let ctx: SharedTestContext;
    let assetsPage: AssetsManagerPage;

    test.beforeAll(async ({ browser, request }) => {
      ctx = await createLoggedInContext(browser, request);

      // Ensure the specific test assets are not ignored (clean state for these assets only)
      await apiEnsureSymbolsNotIgnored(request, TEST_ASSETS_TO_IGNORE);

      // Navigate to assets page once
      assetsPage = new AssetsManagerPage(ctx.sharedPage);
      await assetsPage.visit('asset-manager-managed');
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('add an ignored asset and validate UI message it has been added', async () => {
      ignoredAssets = Number.parseInt(await assetsPage.ignoredAssets());
      await assetsPage.selectShowAll();
      await assetsPage.addIgnoredAsset('1SG');
    });

    test('add another 2 ignored assets and confirm count increased by 3', async () => {
      // Refresh to clear any pending operations from previous test
      await ctx.sharedPage.locator('button', { hasText: 'Refresh' }).first().click();
      await ctx.sharedPage.locator('div[class*=thead__loader]').waitFor({ state: 'detached' });
      await assetsPage.addIgnoredAsset('ZIX');
      await assetsPage.addIgnoredAsset('1CR');
      await assetsPage.ignoredAssetCount(ignoredAssets + 3);
    });

    test('remove an ignored asset, and confirm count decreased by one', async () => {
      // Click refresh to get fresh state (clear any pending operations)
      await ctx.sharedPage.locator('button', { hasText: 'Refresh' }).first().click();
      await ctx.sharedPage.locator('div[class*=thead__loader]').waitFor({ state: 'detached' });
      await assetsPage.selectShowAll();
      await assetsPage.removeIgnoredAsset('1SG');
      await assetsPage.ignoredAssetCount(ignoredAssets + 2);
    });
  });

  test.describe.serial('add asset', () => {
    let ctx: SharedTestContext;
    let assetsPage: AssetsManagerPage;

    // Unique ID for this test run to avoid conflicts with existing assets
    let uniqueId: string;
    // Test address for EVM asset - use a unique address per run
    let testAddress: string;
    // Symbols for cleanup
    let otherAssetSymbol: string;

    test.beforeAll(async ({ browser, request }) => {
      // Generate unique ID based on timestamp
      uniqueId = Date.now().toString().slice(-6);
      // Generate a pseudo-random address based on uniqueId
      testAddress = `0x${uniqueId.padStart(40, 'f')}`;
      otherAssetSymbol = `OTH${uniqueId}`;

      ctx = await createLoggedInContext(browser, request);

      // Navigate to assets page once
      assetsPage = new AssetsManagerPage(ctx.sharedPage);
      await assetsPage.visit('asset-manager-managed');
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('adds an EVM asset', async () => {
      await assetsPage.addAnEvmAsset(testAddress, uniqueId);
    });

    test('adds a non EVM asset', async () => {
      await assetsPage.addOtherAsset(uniqueId);
    });

    test('edit an asset', async () => {
      await assetsPage.editEvmAsset(testAddress, uniqueId);
    });

    test('should delete the assets', async () => {
      await assetsPage.deleteAnEvmAsset(testAddress);
      await assetsPage.deleteOtherAsset(otherAssetSymbol);
    });
  });
});
