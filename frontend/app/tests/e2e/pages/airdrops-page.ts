import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

// Checksummed addresses used only inside the mocked airdrop payload. They are
// rendered by the frontend and never sent back to the backend.
const ADDRESS_ONE = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
const ADDRESS_TWO = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2';

// Fixed cutoff timestamps (seconds) so the 'missed' vs 'unclaimed' split is
// deterministic regardless of when the suite runs.
const CUTOFF_PAST = 1_600_000_000; // 2020-09-13
const CUTOFF_FUTURE = 4_102_444_800; // 2100-01-01

/**
 * Backend-shaped (snake_case) airdrops payload. The frontend camelCases every
 * key on receipt, so it is written here exactly as the backend would return it.
 *
 * The mix is chosen to exercise every status branch:
 * - uniswap    -> claimed
 * - gitcoin    -> unclaimed (decoder present, cutoff in the future)
 * - shapeshift -> unknown (no decoder)
 * - badger     -> missed (decoder present, unclaimed, cutoff in the past)
 * - poap       -> expandable POAP delivery details
 */
const AIRDROPS_RESULT = {
  [ADDRESS_ONE]: {
    gitcoin: { amount: '150.5', asset: 'ETH', claimed: false, cutoff_time: CUTOFF_FUTURE, has_decoder: true, link: 'https://gitcoin.co' },
    uniswap: { amount: '400', asset: 'ETH', claimed: true, has_decoder: true, link: 'https://app.uniswap.org' },
  },
  [ADDRESS_TWO]: {
    badger: { amount: '12', asset: 'ETH', claimed: false, cutoff_time: CUTOFF_PAST, has_decoder: true, link: 'https://badger.com' },
    poap: [
      { assets: [1], event: 'yfi_og', link: 'https://poap.xyz/1', name: 'YFI OG' },
    ],
    shapeshift: { amount: '340', asset: 'ETH', claimed: false, has_decoder: false, link: 'https://shapeshift.com' },
  },
};

export const AIRDROP_STATUS = {
  all: 'All',
  claimed: 'Claimed',
  missed: 'Missed',
  unclaimed: 'Unclaimed',
  unknown: 'Unknown',
} as const;

export class AirdropsPage {
  private nextTaskId = 990_001;
  private readonly airdropTaskIds = new Set<number>();

  constructor(private readonly page: Page) {}

  /**
   * Number of times the airdrops query endpoint has been triggered. Grows once
   * on the initial mount and once per manual refresh.
   */
  get triggerCount(): number {
    return this.airdropTaskIds.size;
  }

  /**
   * Intercepts the airdrops query pipeline so the page renders a deterministic
   * dataset. The airdrops endpoint returns an async task; the task list and
   * task-result endpoints are mocked to complete it with {@link AIRDROPS_RESULT}.
   * Must be called before navigating to the page.
   */
  async setupMocks(): Promise<void> {
    // Query endpoint -> hand out a fresh task id on every call (mount + refresh).
    await this.page.route('**/api/1/blockchains/eth/airdrops**', async (route) => {
      const id = this.nextTaskId++;
      this.airdropTaskIds.add(id);
      await route.fulfill({
        body: JSON.stringify({ message: '', result: { task_id: id } }),
        contentType: 'application/json',
        status: 200,
      });
    });

    // Metadata -> empty, so airdrop source labels fall back to the raw identifier.
    await this.page.route('**/api/1/airdrops/metadata', async (route) => {
      await route.fulfill({
        body: JSON.stringify({ message: '', result: [] }),
        contentType: 'application/json',
        status: 200,
      });
    });

    // Task list -> merge our completed airdrop task ids into the real response so
    // unrelated background tasks keep resolving normally.
    await this.page.route('**/api/1/tasks', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }
      const response = await route.fetch();
      const json = await response.json();
      const result = json.result ?? { completed: [], pending: [] };
      const completed = Array.from(new Set([...(result.completed ?? []), ...this.airdropTaskIds]));
      await route.fulfill({ json: { ...json, result: { ...result, completed } }, response });
    });

    // Task result -> serve the airdrops payload only for our own task ids.
    await this.page.route('**/api/1/tasks/*', async (route) => {
      const id = Number(new URL(route.request().url()).pathname.split('/').pop());
      if (route.request().method() === 'GET' && this.airdropTaskIds.has(id)) {
        await route.fulfill({
          body: JSON.stringify({
            message: '',
            result: { outcome: { message: '', result: AIRDROPS_RESULT }, status: 'completed', status_code: 200 },
          }),
          contentType: 'application/json',
          status: 200,
        });
      }
      else {
        await route.continue();
      }
    });
  }

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'airdrops');
  }

  private table(): Locator {
    return this.page.getByTestId('airdrop-table');
  }

  private rows(): Locator {
    return this.table().locator('tbody tr[data-id="row"]');
  }

  rowFor(source: string): Locator {
    return this.rows().filter({ hasText: source });
  }

  async waitForLoaded(): Promise<void> {
    await expect(this.rows().first()).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectRowCount(count: number): Promise<void> {
    await expect(this.rows()).toHaveCount(count);
  }

  async expectRowVisible(source: string): Promise<void> {
    await expect(this.rowFor(source)).toHaveCount(1);
  }

  async expectRowMissing(source: string): Promise<void> {
    await expect(this.rowFor(source)).toHaveCount(0);
  }

  async selectStatus(label: string): Promise<void> {
    await this.page.getByTestId('airdrop-status-filter').locator('[data-id=activator]').click();
    const menu = this.page.locator('[role=menu]').last();
    await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
    const option = menu.getByText(label, { exact: true }).first();
    await option.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
    await option.click();
    await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_SHORT });
  }

  async expectUnknownAlertVisible(): Promise<void> {
    await expect(this.page.getByTestId('airdrop-unknown-alert')).toBeVisible();
  }

  async expandPoapRow(): Promise<void> {
    const row = this.rowFor('poap').first();
    await row.locator('button').last().click();
  }

  async expectPoapDetail(name: string): Promise<void> {
    await expect(this.page.getByText(name)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async refresh(): Promise<void> {
    await this.page.getByTestId('airdrop-refresh').click();
  }
}
