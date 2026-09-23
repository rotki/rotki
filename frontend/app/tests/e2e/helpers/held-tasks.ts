import { expect, type Page, type Route } from '@playwright/test';

async function fulfillJson(route: Route, result: unknown): Promise<void> {
  await route.fulfill({
    body: JSON.stringify({ message: '', result }),
    contentType: 'application/json',
    status: 200,
  });
}

function taskIdOf(route: Route): number {
  return Number(new URL(route.request().url()).pathname.split('/').pop());
}

/**
 * Keeps chosen async queries running for as long as a test needs.
 *
 * @remarks
 * A held query is answered with a task id of its own that `GET /tasks` keeps listing as pending, so
 * the app sees the work as running until it is cancelled. A `DELETE` of a held task is accepted
 * and recorded without reaching the backend. Everything else, including the app's own background
 * tasks, falls through to the real backend.
 *
 * Call {@link install} before starting any held query.
 */
export class HeldTasks {
  private nextTaskId = 880_001;
  private readonly held = new Map<number, string>();
  private readonly cancelled: string[] = [];

  constructor(private readonly page: Page) {}

  async install(): Promise<void> {
    await this.page.route('**/api/1/tasks', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }
      const response = await route.fetch();
      const json = await response.json();
      const result = json.result ?? { completed: [], pending: [] };
      const heldIds = [...this.held.keys()];
      const pending = Array.from(new Set([...(result.pending ?? []), ...heldIds]));
      const completed = (result.completed ?? []).filter((id: number) => !this.held.has(id));
      await route.fulfill({ json: { ...json, result: { ...result, completed, pending } }, response });
    });

    await this.page.route('**/api/1/tasks/*', async (route) => {
      const id = taskIdOf(route);
      const label = this.held.get(id);
      if (route.request().method() !== 'DELETE' || label === undefined) {
        await route.continue();
        return;
      }
      this.held.delete(id);
      this.cancelled.push(label);
      await fulfillJson(route, true);
    });
  }

  /**
   * Answers every request `matches` accepts with a new held task.
   *
   * @param label - names the query in {@link expectCancelled}
   * @param matches - picks the query's request by URL
   */
  async hold(label: string, matches: (url: URL) => boolean): Promise<void> {
    await this.page.route(matches, async (route) => {
      const id = this.nextTaskId++;
      this.held.set(id, label);
      await fulfillJson(route, { task_id: id });
    });
  }

  /** Waits until exactly these held queries were cancelled, in any order. */
  async expectCancelled(labels: string[]): Promise<void> {
    await expect.poll(() => [...this.cancelled].sort()).toEqual([...labels].sort());
  }
}
