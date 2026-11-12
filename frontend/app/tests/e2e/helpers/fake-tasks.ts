import type { Page, Route } from '@playwright/test';

/** Task ids handed out by the fakes, far above anything the real backend reaches in a run. */
const FAKE_TASK_ID_START = 900_000;

export async function fulfillJson(route: Route, result: unknown, status = 200): Promise<void> {
  await route.fulfill({
    body: JSON.stringify({ message: '', result }),
    contentType: 'application/json',
    status,
  });
}

export interface FakeTasks {
  /**
   * Registers a completed task and returns its id, for a faked async query to answer with.
   *
   * @remarks
   * A `message` with a `null` result is how the backend reports a failed task.
   */
  start: (result: unknown, message?: string) => number;
}

const installed = new WeakMap<Page, FakeTasks>();

/**
 * Serves faked async tasks on `/tasks`, once per page however many fakes ask for it.
 *
 * @remarks
 * The app polls one `/tasks` endpoint for every task, so the list comes from the real backend with the
 * fake ids appended, and real tasks keep resolving. A second route on the same URL would take over the
 * first and never list its ids, which is why every fake on a page shares this one registry.
 */
export async function installFakeTasks(page: Page): Promise<FakeTasks> {
  const existing = installed.get(page);
  if (existing)
    return existing;

  let nextTaskId = FAKE_TASK_ID_START;
  const outcomes = new Map<number, { result: unknown; message: string }>();
  const tasks: FakeTasks = {
    start: (result, message = '') => {
      const id = nextTaskId++;
      outcomes.set(id, { message, result });
      return id;
    },
  };
  installed.set(page, tasks);

  await page.route('**/api/1/tasks', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    const response = await route.fetch();
    const body = await response.json();
    body.result.completed = [...(body.result.completed ?? []), ...outcomes.keys()];
    await route.fulfill({ json: body, response });
  });

  await page.route('**/api/1/tasks/*', async (route) => {
    const id = Number(new URL(route.request().url()).pathname.split('/').pop());
    const outcome = outcomes.get(id);
    if (!outcome || route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    outcomes.delete(id);
    await fulfillJson(route, { outcome, status: 'completed', status_code: 200 });
  });

  return tasks;
}
