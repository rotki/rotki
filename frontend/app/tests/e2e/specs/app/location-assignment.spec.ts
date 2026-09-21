import path from 'node:path';
import { type APIRequestContext, expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { apiCustomLocation, apiLocationAliases, type ApiLocationNode, apiLocationTree } from '../../helpers/locations-api';
import { EVENT_ROW } from '../../pages/history-event-rows';
import { HistoryEventsPage } from '../../pages/history-events-page';
import { ImportPage } from '../../pages/import-page';
import { LocationManagerPage } from '../../pages/location-manager-page';
import { ManualBalancesPage } from '../../pages/manual-balances-page';
import { PillFilterBar } from '../../pages/pill-filter-bar';

/** Names `ING`, which two custom locations share, and `Nordbank`, which no location has. */
const IMPORT_CSV = path.resolve(import.meta.dirname, '..', '..', 'fixtures', 'import', 'rotki_events_custom_locations.csv');
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
  let ingBank: ApiLocationNode;
  let ingBroker: ApiLocationNode;
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

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    manager = new LocationManagerPage(ctx.sharedPage);
    await manager.visit();
    for (const parent of ['banks', 'exchanges']) {
      await manager.addChildOf(parent);
      await manager.fillName('ING');
      await manager.saveForm();
      await manager.expectFormClosed();
    }
    const tree = await apiLocationTree(request);
    const ingBelow = (parent: string): ApiLocationNode | undefined => tree.find(node => node.name === 'ING' && node.parent_identifier === parent);
    const [bank, broker] = [ingBelow('banks'), ingBelow('exchanges')];
    if (!bank || !broker)
      throw new Error('The two ING locations were not created');
    [ingBank, ingBroker] = [bank, broker];
  });

  test.beforeEach(({ request }) => {
    api = request;
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('offers only the same-named locations for an ambiguous import value and names them by path', async () => {
    const importPage = new ImportPage(ctx.sharedPage);
    await importPage.visit();
    await importPage.selectSource('Custom');
    await importPage.uploadFile('rotki_events', IMPORT_CSV);
    await importPage.submitImport('rotki_events');

    expect((await importPage.unresolvedLocationValues()).sort()).toEqual(['ING', NEW_BANK]);
    expect((await importPage.locationChoiceOptions('ING')).sort()).toEqual([ingBank.identifier, ingBroker.identifier].sort());

    await importPage.mapLocationValue('ING', 'ING', ingBank.identifier);
    await expect(importPage.locationChoiceSelection('ING')).toHaveText('Banks › ING');
  });

  test('creates a location for an unknown import value and imports with it', async () => {
    const importPage = new ImportPage(ctx.sharedPage);
    await importPage.createLocationFor(NEW_BANK);
    await manager.waitForForm();
    await expect(manager.formName()).toHaveValue(NEW_BANK);
    await manager.selectParent('Banks', 'banks');
    await manager.saveForm();

    nordbank = await customLocation(NEW_BANK);
    expect(nordbank.parent_identifier).toBe('banks');
    await expect(importPage.locationChoiceSelection(NEW_BANK)).toHaveText(NEW_BANK);

    await importPage.confirmLocationMapping();
    await importPage.waitForImportComplete('rotki_events');
    await importPage.dismissNotifications();

    await expect.poll(async () => (await apiLocationAliases(api)).sort((a, b) => a.alias.localeCompare(b.alias)), { timeout: TIMEOUT_MEDIUM })
      .toEqual([
        { alias: 'ING', location_identifier: ingBank.identifier },
        { alias: NEW_BANK, location_identifier: nordbank.identifier },
      ]);
  });

  test('files each imported event under the location it was mapped to', async () => {
    const history = new HistoryEventsPage(ctx.sharedPage);
    await history.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    const bar = new PillFilterBar(ctx.sharedPage);
    await bar.addField('location');
    await bar.selectValueOnce(ingBank.identifier, 'ING');
    await bar.closeEditor();

    await expect(ctx.sharedPage.locator(EVENT_ROW)).toHaveCount(1, { timeout: TIMEOUT_MEDIUM });
    await expect(ctx.sharedPage.locator('[data-testid=event-amount]').filter({ hasText: '100.00' })).toHaveCount(1);
  });

  test('assigns a manual balance to a custom location', async () => {
    const balances = new ManualBalancesPage(ctx.sharedPage);
    await balances.visit();
    await balances.openAddDialog();
    await balances.addBalance(MANUAL_BALANCE);

    await balances.balanceShouldMatch([MANUAL_BALANCE]);
  });

  test('links from what uses a location to the page listing it', async () => {
    await manager.visit();
    await manager.search(NEW_BANK);
    await manager.requestDelete(nordbank.identifier);

    const usage = manager.usageDialog();
    await expect(usage.getByTestId('location-usage-entry').filter({ hasText: 'Manual balances' })).toContainText('1');
    await expect(usage.getByTestId('location-usage-entry').filter({ hasText: 'History events' })).toContainText('1');
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
    const balances = new ManualBalancesPage(ctx.sharedPage);

    async function offeredBelowBanks(): Promise<string[]> {
      await balances.visit();
      await balances.openAddDialog();
      const offered = await balances.locationOptionsFor('Banks');
      await balances.cancelDialog();
      return offered;
    }

    expect(await offeredBelowBanks()).toEqual(expect.arrayContaining([ingBank.identifier, nordbank.identifier]));

    await manager.visit();
    await manager.search(NEW_BANK);
    await manager.toggleArchive(nordbank.identifier);
    await expect.poll(async () => (await customLocation(NEW_BANK)).is_active, { timeout: TIMEOUT_MEDIUM }).toBe(false);

    const afterArchive = await offeredBelowBanks();
    expect(afterArchive).toContain(ingBank.identifier);
    expect(afterArchive).not.toContain(nordbank.identifier);
  });
});
