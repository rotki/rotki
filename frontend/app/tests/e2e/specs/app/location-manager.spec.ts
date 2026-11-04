import { type APIRequestContext, expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { apiAddOnlineEvent } from '../../helpers/history-events-api';
import { apiCustomLocation, apiLocationAliases, type ApiLocationNode } from '../../helpers/locations-api';
import { EVENT_ROW } from '../../pages/history-event-rows';
import { HistoryEventsPage } from '../../pages/history-events-page';
import { LocationManagerPage } from '../../pages/location-manager-page';
import { PillFilterBar } from '../../pages/pill-filter-bar';

const PARENT = 'Harbor OTC';
const CHILD = 'Pier Account';
const SCRATCH = 'Scratch Location';

/** One event is recorded at each custom location, so both are in use and the parent's history spans the two. */
const PARENT_AMOUNT = '0.50';
const CHILD_AMOUNT = '1,000.00';

test.describe.serial('location manager', () => {
  let ctx: SharedTestContext;
  let manager: LocationManagerPage;
  let parent: ApiLocationNode;
  let child: ApiLocationNode;
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
  });

  test.beforeEach(({ request }) => {
    api = request;
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('adds a custom location below a built-in one', async () => {
    await manager.addChildOf('exchanges');
    await manager.fillName(PARENT);
    await manager.saveForm();
    await manager.expectFormClosed();

    parent = await customLocation(PARENT);
    expect(parent.parent_identifier).toBe('exchanges');
    expect(parent.identifier).toMatch(/^custom:/);
    await expect(manager.row(parent.identifier)).toContainText(PARENT);
    await expect(manager.row(parent.identifier)).toContainText('Custom');
  });

  test('nests a location below a custom one', async () => {
    await manager.addChildOf(parent.identifier);
    await manager.fillName(CHILD);
    await manager.saveForm();
    await manager.expectFormClosed();

    child = await customLocation(CHILD);
    expect(child.parent_identifier).toBe(parent.identifier);
    await expect(manager.row(child.identifier)).toBeVisible();
  });

  test('rejects a name a sibling already has', async () => {
    await manager.addChildOf('exchanges');
    await manager.fillName(PARENT.toUpperCase());
    await manager.saveForm();

    // The backend compares sibling names without case; the form stays open and names the refusal.
    await expect(ctx.sharedPage.getByTestId('location-form-error')).toContainText('already exists', { timeout: TIMEOUT_MEDIUM });
    await expect(ctx.sharedPage.getByTestId('location-form')).toBeVisible();
    await manager.discardForm();
    await expect(manager.rowNames().filter({ hasText: new RegExp(`^${PARENT}$`, 'i') })).toHaveCount(1);
  });

  test('keeps the ancestors of a search match in the tree', async () => {
    await manager.search('Pier');
    await expect(manager.rowNames()).toHaveText(['Exchanges', PARENT, CHILD]);
    await manager.search('');
  });

  test('creates a location from a search with no match', async () => {
    await manager.search(SCRATCH);
    await manager.createFromSearch();
    await expect(manager.formName()).toHaveValue(SCRATCH);
    await manager.selectParent('Other', 'other');
    await manager.saveForm();
    await manager.expectFormClosed();
    await manager.search('');

    const scratch = await customLocation(SCRATCH);
    expect(scratch.parent_identifier).toBe('other');
  });

  test('moves a location only after the user confirms the new path', async () => {
    const scratch = await customLocation(SCRATCH);
    await manager.edit(scratch.identifier);
    await manager.selectParent('Banks', 'banks');
    await manager.saveForm();

    const move = manager.moveNotice();
    await expect(move).toContainText('Move location');
    await expect(move).toContainText(`Other › ${SCRATCH}`);
    await expect(move).toContainText(`Banks › ${SCRATCH}`);
    expect((await customLocation(SCRATCH)).parent_identifier).toBe('other');
    await manager.saveForm();
    await manager.expectFormClosed();

    await expect.poll(async () => (await customLocation(SCRATCH)).parent_identifier, { timeout: TIMEOUT_MEDIUM }).toBe('banks');
  });

  test('deletes a location nothing uses', async () => {
    const scratch = await customLocation(SCRATCH);
    await manager.requestDelete(scratch.identifier);
    await expect(manager.confirmDialog()).toContainText('Delete location');
    await manager.confirm();

    await expect(manager.row(scratch.identifier)).toHaveCount(0);
    await expect.poll(async () => apiCustomLocation(api, SCRATCH), { timeout: TIMEOUT_MEDIUM }).toBeUndefined();
  });

  test('saves an alias for a custom location', async () => {
    await manager.openTab('aliases');
    await manager.addAlias('luno', PARENT, parent.identifier);

    await expect(manager.aliasRow('luno')).toContainText(`Exchanges › ${PARENT}`);
    await expect.poll(async () => apiLocationAliases(api), { timeout: TIMEOUT_MEDIUM })
      .toContainEqual({ alias: 'luno', location_identifier: parent.identifier });
  });

  test('records history at the custom locations', async () => {
    await apiAddOnlineEvent(api, { amount: '0.5', asset: 'ETH', eventSubtype: 'none', eventType: 'receive', groupIdentifier: 'location-manager-parent', location: parent.identifier, sequenceIndex: 0, timestamp: 1700000000000 });
    await apiAddOnlineEvent(api, { amount: '1000', asset: 'EUR', eventSubtype: 'none', eventType: 'receive', groupIdentifier: 'location-manager-child', location: child.identifier, sequenceIndex: 0, timestamp: 1700000001000 });
  });

  test('filters history by a location and every location below it', async () => {
    const history = new HistoryEventsPage(ctx.sharedPage);
    await history.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    const bar = new PillFilterBar(ctx.sharedPage);
    await bar.addField('location');
    await bar.selectValueOnce(parent.identifier, PARENT);
    await bar.closeEditor();
    await bar.expectPillVisible('location');

    // An exact match on the parent would list its own event alone, without its child's.
    await expect(ctx.sharedPage.locator(EVENT_ROW)).toHaveCount(2, { timeout: TIMEOUT_MEDIUM });
    const amounts = ctx.sharedPage.locator('[data-testid=event-amount]');
    await expect(amounts.filter({ hasText: PARENT_AMOUNT })).toHaveCount(1);
    await expect(amounts.filter({ hasText: CHILD_AMOUNT })).toHaveCount(1);
  });

  test('lists what uses a location instead of deleting it', async () => {
    await manager.visit();
    await manager.requestDelete(parent.identifier);

    const usage = manager.usageNotice();
    await expect(usage).toContainText(`Exchanges › ${PARENT} is in use`);
    await expect(usage.getByTestId('location-usage-entry').filter({ hasText: 'History events' })).toContainText('1');
    await expect(usage.getByTestId('location-usage-entry').filter({ hasText: 'Locations below it' })).toContainText('1');
    await manager.closeUsage();

    expect((await customLocation(PARENT)).is_active).toBe(true);
  });

  test('opens the history of a location, and of the locations below it, from what uses it', async () => {
    await manager.requestDelete(parent.identifier);
    await manager.openUsageLink('History events');

    await expect(ctx.sharedPage).toHaveURL(/\/history/);
    await new PillFilterBar(ctx.sharedPage).expectPillVisible('location');
    await expect(ctx.sharedPage.locator(EVENT_ROW)).toHaveCount(2, { timeout: TIMEOUT_MEDIUM });
  });

  test('archives a used location from its usage and keeps it listed on this visit', async () => {
    await manager.visit();
    await manager.search(CHILD);
    await manager.requestDelete(child.identifier);
    await expect(manager.usageNotice()).toContainText(`Exchanges › ${PARENT} › ${CHILD} is in use`);
    await manager.archiveFromUsage();

    await expect.poll(async () => (await customLocation(CHILD)).is_active, { timeout: TIMEOUT_MEDIUM }).toBe(false);
    await expect(manager.row(child.identifier)).toContainText('Archived');
  });

  test('hides archived locations on a fresh visit unless asked to show them', async () => {
    await new HistoryEventsPage(ctx.sharedPage).visit();
    await manager.visit();
    await manager.search(PARENT);
    await expect(manager.row(parent.identifier)).toBeVisible();
    await manager.search(CHILD);
    await expect(manager.row(child.identifier)).toHaveCount(0);

    await manager.setShowArchived(true);
    await expect(manager.row(child.identifier)).toContainText('Archived');
  });

  test('deletes an alias only once confirmed', async () => {
    await manager.visit();
    await manager.openTab('aliases');
    await expect(manager.aliasRow('luno')).toBeVisible();

    await manager.deleteAlias('luno');

    await expect(manager.aliasRow('luno')).toHaveCount(0);
    await expect.poll(async () => apiLocationAliases(api), { timeout: TIMEOUT_MEDIUM }).toEqual([]);
  });
});
