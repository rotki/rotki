import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { HeldTasks } from '../../helpers/held-tasks';
import { RotkiApp } from '../../pages/rotki-app';
import { TaskDockPage } from '../../pages/task-dock-page';

const AIRDROPS = 'Airdrops';
const ALL_BALANCES = 'All balances';
const PNL_REPORT = 'Profit & loss report';

/**
 * The prompt's note that jobs changing data keep running, whatever their number.
 *
 * @remarks
 * The shard's backend is shared with earlier specs, so the app may be running a data-changing task
 * of its own next to the report; only the note's presence is the report's doing.
 */
const KEPT_RUNNING = /\d+ tasks? that changes? your data keeps? running/;

function isAsyncQuery(url: URL, path: string): boolean {
  return url.pathname.endsWith(path) && url.searchParams.get('async_query') === 'true';
}

test.describe.serial('task dock', () => {
  let ctx: SharedTestContext;
  let dock: TaskDockPage;
  let held: HeldTasks;
  let reportProgress = 0;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    const page = ctx.sharedPage;
    dock = new TaskDockPage(page);
    held = new HeldTasks(page);

    await held.install();
    await held.hold('airdrops', url => url.pathname.endsWith('/api/1/blockchains/eth/airdrops'));
    await held.hold('balances', url => isAsyncQuery(url, '/api/1/balances'));
    await held.hold('pnl', url => isAsyncQuery(url, '/api/1/history'));

    await page.route('**/api/1/airdrops/metadata', async route => route.fulfill({ json: { message: '', result: [] } }));
    await page.route('**/api/1/history/status', async route => route.fulfill({
      json: { message: '', result: { processing_state: 'Processing events', total_progress: String(reportProgress) } },
    }));
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('offers Stop all for two stoppable jobs, and cancelling the prompt keeps them running', async () => {
    const page = ctx.sharedPage;
    await page.getByTestId('snapshot-action').click();
    await page.getByRole('button', { name: 'Force save' }).click();
    await RotkiApp.navigateTo(page, 'airdrops');

    await dock.openPanel();
    await dock.expectRow(AIRDROPS, 'running');
    await dock.expectRow(ALL_BALANCES, 'running');
    await dock.expectStopAllOffered(true);

    await dock.stopAll();
    await dock.expectDialog('Stop all', 'This stops 2 refreshes and syncs.');
    await dock.dismissDialog();

    await dock.expectRow(AIRDROPS, 'running');
    await dock.expectRow(ALL_BALANCES, 'running');
    await held.expectCancelled([]);
  });

  test('names the job that changes data and stops only the others', async () => {
    const page = ctx.sharedPage;
    await RotkiApp.navigateTo(page, 'profit-loss-report');
    const generate = page.getByRole('button', { name: 'Generate' });
    await expect(generate).toBeEnabled();
    await generate.click();

    await dock.openPanel();
    await dock.expectRow(PNL_REPORT, 'running');

    await dock.stopAll();
    await dock.expectDialog('Stop all', 'This stops 2 refreshes and syncs.');
    await dock.expectDialog('Stop all', KEPT_RUNNING);
    await dock.confirmDialog();

    await held.expectCancelled(['airdrops', 'balances']);
    await dock.expectRow(AIRDROPS, 'cancelled');
    await dock.expectRow(ALL_BALANCES, 'cancelled');
    await dock.expectRow(PNL_REPORT, 'running');
    await dock.expectStopAllOffered(false);
  });

  test('moves the report row meter with the reported progress, and its own cancel stops it', async () => {
    reportProgress = 37;
    await dock.expectRowMeter(PNL_REPORT, '37 of 100');
    reportProgress = 64;
    await dock.expectRowMeter(PNL_REPORT, '64 of 100');

    await dock.cancelRow(PNL_REPORT);
    await dock.expectDialog('Stop', 'leaves it unfinished');
    await dock.confirmDialog();

    await held.expectCancelled(['airdrops', 'balances', 'pnl']);
    await dock.expectRow(PNL_REPORT, 'cancelled');
  });
});
