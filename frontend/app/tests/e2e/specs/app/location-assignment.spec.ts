import path from 'node:path';
import { type APIRequestContext, expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { apiCustomLocation, type ApiLocationNode } from '../../helpers/locations-api';
import { LocationManagerPage } from '../../pages/location-manager-page';
import { ManualBalancesPage } from '../../pages/manual-balances-page';

const LOCATION_IMAGE = path.resolve(import.meta.dirname, '..', '..', '..', '..', 'public', 'favicon-16x16.png');

const NEW_BANK = 'Nordbank';
const MANUAL_BALANCE = {
  amount: '75',
  asset: 'EUR',
  keyword: 'EUR',
  label: 'Nordbank savings',
  location: NEW_BANK,
  tags: [],
};

test.describe.serial('assigning custom locations', () => {
  let ctx: SharedTestContext;
  let manager: LocationManagerPage;
  let balances: ManualBalancesPage;
  let nordbank: ApiLocationNode;
  /** The request fixture of the running test: Playwright refuses the one from `beforeAll` inside a test. */
  let api: APIRequestContext;

  async function customLocation(name: string): Promise<ApiLocationNode> {
    let found: ApiLocationNode | undefined;
    await expect.poll(async () => {
      found = await apiCustomLocation(api, name);
      return found;
    }, { timeout: TIMEOUT_MEDIUM }).toBeDefined();
    return found!;
  }

  /** The locations a new manual balance is offered when searching for banks. */
  async function offeredBanks(): Promise<string[]> {
    await balances.visit();
    await balances.openAddDialog();
    const offered = await balances.locationOptionsFor('Banks');
    await balances.cancelDialog();
    return offered;
  }

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    manager = new LocationManagerPage(ctx.sharedPage);
    balances = new ManualBalancesPage(ctx.sharedPage);
    api = request;
    await manager.visit();
    await manager.addChildOf('banks');
    await manager.fillName(NEW_BANK);
    await manager.saveForm();
    await manager.expectFormClosed();
    nordbank = await customLocation(NEW_BANK);
  });

  test.beforeEach(({ request }) => {
    api = request;
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('assigns a manual balance to a custom location', async () => {
    await balances.visit();
    await balances.openAddDialog();
    await balances.addBalance(MANUAL_BALANCE);

    await balances.balanceShouldMatch([MANUAL_BALANCE]);
  });

  test('links from a location\'s manual balances to the page listing them', async () => {
    await manager.visit();
    await manager.search(NEW_BANK);
    await manager.requestDelete(nordbank.identifier);

    const usage = manager.usageNotice();
    await expect(usage.getByTestId('location-usage-entry').filter({ hasText: 'Manual balances' })).toContainText('1');
    await manager.openUsageLink('Manual balances');

    await expect(ctx.sharedPage).toHaveURL(/\/balances\/manual/);
  });

  test('uploads an image for a custom location and removes it again', async () => {
    await manager.visit();
    await manager.search(NEW_BANK);
    await manager.edit(nordbank.identifier);
    await manager.chooseImage(LOCATION_IMAGE);
    await manager.saveForm();
    await manager.expectFormClosed();

    await expect.poll(async () => (await customLocation(NEW_BANK)).image, { timeout: TIMEOUT_MEDIUM }).not.toBeNull();
    await expect(manager.row(nordbank.identifier).locator('img')).toHaveAttribute('src', /\/image\?v=/);

    await manager.edit(nordbank.identifier);
    await manager.removeImage();
    await manager.saveForm();
    await manager.expectFormClosed();

    await expect.poll(async () => (await customLocation(NEW_BANK)).image, { timeout: TIMEOUT_MEDIUM }).toBeNull();
    await expect(manager.row(nordbank.identifier).locator('img')).toHaveCount(0);
  });

  test('stops offering an archived location for new manual balances', async () => {
    expect(await offeredBanks()).toContain(nordbank.identifier);

    await manager.visit();
    await manager.search(NEW_BANK);
    await manager.requestDelete(nordbank.identifier);
    await manager.archiveFromUsage();
    await expect.poll(async () => (await customLocation(NEW_BANK)).is_active, { timeout: TIMEOUT_MEDIUM }).toBe(false);

    expect(await offeredBanks()).not.toContain(nordbank.identifier);
  });
});
