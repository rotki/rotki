import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { apiEnsureSymbolsNotIgnored } from '../../helpers/api';
import { apiConfigureRpcMock } from '../../helpers/rpc-mock';
import { AssetsManagerPage } from '../../pages/assets-manager-page';
import { CustomAssetsPage } from '../../pages/custom-assets-page';
import { LatestPricePage } from '../../pages/price-manager-page';

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
      await expect(ctx.sharedPage.locator('[data-id="thead-loader"]')).toHaveCount(0);
      await assetsPage.addIgnoredAsset('ZIX');
      await assetsPage.addIgnoredAsset('1CR');
      await assetsPage.ignoredAssetCount(ignoredAssets + 3);
    });

    test('remove an ignored asset, and confirm count decreased by one', async () => {
      // Click refresh to get fresh state (clear any pending operations)
      await ctx.sharedPage.locator('button', { hasText: 'Refresh' }).first().click();
      await expect(ctx.sharedPage.locator('[data-id="thead-loader"]')).toHaveCount(0);
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

      // Point Ethereum at the mock RPC so the ERC20 token-detail lookup resolves locally
      // instead of querying live public nodes (which rate-limit and stall the dialog).
      await apiConfigureRpcMock(request, 'ETH');

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

  test.describe.serial('custom assets', () => {
    let ctx: SharedTestContext;
    let customPage: CustomAssetsPage;

    const uniqueId = Date.now().toString().slice(-6);
    const assetName = `Original-${uniqueId}`;
    const renamedName = `Modified-${uniqueId}`;
    const assetType = `Type-${uniqueId}`;

    test.beforeAll(async ({ browser, request }) => {
      ctx = await createLoggedInContext(browser, request, { disableModules: true });
      customPage = new CustomAssetsPage(ctx.sharedPage);
      await customPage.visit();
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('adds a custom asset', async () => {
      await customPage.addAsset({ name: assetName, type: assetType, notes: 'initial notes' });
      await customPage.expectRow(assetName);
    });

    test('edits a custom asset', async () => {
      await customPage.editAsset(assetName, { newName: renamedName, newNotes: 'updated notes' });
      await customPage.expectRow(renamedName);
      await customPage.expectNoRow(assetName);
    });

    test('deletes a custom asset', async () => {
      await customPage.deleteAsset(renamedName);
      await customPage.expectNoRow(renamedName);
    });

    test('shows validation errors when required fields are empty', async () => {
      await customPage.openDialog();
      await customPage.submitDialog();
      await customPage.expectRequiredErrors();
      await customPage.cancelDialog();
    });

    test('cancel button closes the add dialog', async () => {
      await customPage.openDialog();
      await customPage.cancelDialog();
    });
  });

  test.describe.serial('custom asset + custom price', () => {
    let ctx: SharedTestContext;
    let customPage: CustomAssetsPage;
    let pricePage: LatestPricePage;

    const uniqueId = Date.now().toString().slice(-6);
    const assetName = `PricedCustom-${uniqueId}`;
    const assetType = `PricedType-${uniqueId}`;

    test.beforeAll(async ({ browser, request }) => {
      ctx = await createLoggedInContext(browser, request, { disableModules: true });
      customPage = new CustomAssetsPage(ctx.sharedPage);
      pricePage = new LatestPricePage(ctx.sharedPage);
    });

    test.afterAll(async () => {
      await cleanupContext(ctx);
    });

    test('adds a custom asset with a latest price', async () => {
      await customPage.visit();
      await customPage.addAsset({ name: assetName, type: assetType });
      await customPage.expectRow(assetName);

      await pricePage.visit();
      await pricePage.addPrice(assetName, 'USD', '4242');
      await pricePage.expectRowWithValue('4,242');
    });

    test('cleans up the price and the custom asset', async () => {
      await pricePage.visit();
      await pricePage.deletePrice('4,242');

      await customPage.visit();
      await customPage.deleteAsset(assetName);
      await customPage.expectNoRow(assetName);
    });
  });
});
