import type { Page } from '@playwright/test';
import { fulfillJson, installFakeTasks } from './fake-tasks';

type FakeAssetBalances = Record<string, { amount: string; value: string }>;

export interface FakeExchangeConnection {
  /** A UUID, as the backend gives connections, so the response key transform is exercised on real-shaped keys. */
  identifier: string;
  location: string;
  name: string;
  balances: FakeAssetBalances;
}

export interface FakeExchangeSetup {
  connections: FakeExchangeConnection[];
  /**
   * Connection identifiers whose balance query fails, with the message the backend would report.
   *
   * @remarks
   * Mutable, so a spec can let a later refresh succeed.
   */
  failing: Record<string, string>;
}

function sumBalances(balances: FakeAssetBalances[]): FakeAssetBalances {
  const total: FakeAssetBalances = {};
  for (const balance of balances) {
    for (const [asset, { amount, value }] of Object.entries(balance)) {
      const previous = total[asset];
      total[asset] = previous
        ? { amount: String(Number(previous.amount) + Number(amount)), value: String(Number(previous.value) + Number(value)) }
        : { amount, value };
    }
  }
  return total;
}

/**
 * Stands in for the backend's exchange connections and their balance queries.
 *
 * @remarks
 * Install before the app loads the account: a fresh login takes its connections from the login
 * result, but a reload resumes the session through `GET /exchanges`, which is what this fakes, so
 * reload the page after installing. A balance query is an async task, answered the way the backend
 * does: one connection's failure leaves it out of `per_account` and names it in `failed_accounts`.
 * The task is answered through {@link installFakeTasks}.
 */
export async function fakeExchangeEndpoints(page: Page, setup: FakeExchangeSetup): Promise<void> {
  const tasks = await installFakeTasks(page);

  await page.route('**/api/1/exchanges', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await fulfillJson(route, setup.connections.map(({ identifier, location, name }) => ({
      connector: location,
      identifier,
      location,
      name,
      ...(location === 'kraken' ? { kraken_account_type: 'starter' } : {}),
    })));
  });

  await page.route('**/api/1/exchanges/balances/*', async (route) => {
    const location = new URL(route.request().url()).pathname.split('/').pop() ?? '';
    const connections = setup.connections.filter(connection => connection.location === location);
    const healthy = connections.filter(({ identifier }) => !(identifier in setup.failing));
    const failed = connections.filter(({ identifier }) => identifier in setup.failing);

    const id = tasks.start({
      failed_accounts: failed.length > 0
        ? { [location]: Object.fromEntries(failed.map(({ identifier }) => [identifier, { cause: 'network', message: setup.failing[identifier] }])) }
        : {},
      per_account: { [location]: Object.fromEntries(healthy.map(({ balances, identifier }) => [identifier, balances])) },
      totals: { [location]: sumBalances(healthy.map(({ balances }) => balances)) },
    });
    await fulfillJson(route, { task_id: id });
  });
}
