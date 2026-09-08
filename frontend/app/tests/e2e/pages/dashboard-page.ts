import { expect, type Locator, type Page } from '@playwright/test';
import { type BigNumber, Zero } from '@rotki/common';
import { parseBigNumber, updateLocationBalance } from '../helpers/utils';
import { RotkiApp } from './rotki-app';
import { SnapshotEditorPage } from './snapshot-editor-page';
import { SnapshotImportDialog } from './snapshot-import-dialog';

export class DashboardPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'dashboard');
  }

  /**
   * Reads a settled amount out of an `AmountDisplay`.
   *
   * @remarks
   * While the value is loading the component renders a skeleton and no text at all, so a bare
   * `textContent` can return an empty string that `parseBigNumber` then reads as zero: a balance
   * comparison against it fails for a reason that has nothing to do with the balances. Waiting for
   * the element to hold text is the gate; the read after it is safe.
   */
  private async readAmount(amount: Locator): Promise<BigNumber> {
    await expect(amount).not.toBeEmpty();
    return parseBigNumber(await amount.textContent() ?? '0');
  }

  async getOverallBalance(): Promise<BigNumber> {
    return this.readAmount(
      this.page.locator('[data-testid=overall-balances-net-worth] [data-testid=display-amount]'),
    );
  }

  async getBlockchainBalances(): Promise<Map<string, BigNumber>> {
    await this.page.locator('[data-testid=blockchain-balances]').waitFor({ state: 'visible' });

    const balances = new Map<string, BigNumber>();
    const elements = this.page.locator('[data-testid=blockchain-balance-summary]');
    const count = await elements.count();

    for (let i = 0; i < count; i++) {
      const element = elements.nth(i);
      const location = await element.getAttribute('data-location');
      if (!location)
        continue;

      const amount = element.locator('[data-testid=display-amount]');
      await expect(amount).not.toBeEmpty();
      updateLocationBalance(await amount.textContent() ?? '0', balances, location);
    }

    return balances;
  }

  async getNonFungibleBalances(): Promise<BigNumber> {
    const nftTable = this.page.locator('[data-testid=nft-balance-table]');
    const nftTableExists = (await nftTable.count()) > 0;

    if (!nftTableExists) {
      return Zero;
    }

    const displayAmount = nftTable.locator('tbody tr:last-child td:nth-child(2) [data-testid=display-amount]');
    const displayAmountExists = (await displayAmount.count()) > 0;

    if (!displayAmountExists) {
      return Zero;
    }

    return this.readAmount(displayAmount);
  }

  async getLocationBalances(): Promise<Map<string, BigNumber>> {
    await this.page.locator('[data-testid=manual-balances]').first().waitFor({ state: 'visible' });

    const balances = new Map<string, BigNumber>();
    const elements = this.page.locator('[data-testid=manual-balance-summary]');
    const count = await elements.count();

    for (let i = 0; i < count; i++) {
      const element = elements.nth(i);
      const location = await element.getAttribute('data-location');
      if (!location)
        continue;

      const amount = element.locator('[data-testid=display-amount]');
      await expect(amount).not.toBeEmpty();
      updateLocationBalance(await amount.textContent() ?? '0', balances, location);
    }

    return balances;
  }

  async amountDisplayIsBlurred(): Promise<void> {
    await expect(this.page.locator('[data-testid=amount-display]').first()).toHaveCSS('filter', /^blur/);
  }

  async amountDisplayIsNotBlurred(): Promise<void> {
    await expect(this.page.locator('[data-testid=amount-display]').first()).not.toHaveCSS('filter', /^blur/);
  }

  async percentageDisplayIsBlurred(): Promise<void> {
    await expect(this.page.locator('[data-testid=percentage-display]').first()).toHaveClass(/blur/);
  }

  async percentageDisplayIsNotBlurred(): Promise<void> {
    await expect(this.page.locator('[data-testid=percentage-display]').first()).not.toHaveClass(/blur/);
  }

  async openSnapshotMenu(): Promise<void> {
    await this.page.locator('[data-testid=snapshot-action]').click();
  }

  /**
   * Opens the snapshot import dialog.
   *
   * @remarks
   * Call {@link DashboardPage.openSnapshotMenu} first. The Import button lives inside that menu,
   * so this finds nothing while it is closed.
   */
  async openImportSnapshotDialog(): Promise<SnapshotImportDialog> {
    await this.page.getByRole('button', { name: 'Import', exact: true }).click();
    const dialog = new SnapshotImportDialog(this.page);
    await dialog.waitForVisible();
    return dialog;
  }

  /**
   * Clicks the rendered data point on the net-worth chart to open the snapshot
   * editor page. With a single seeded snapshot 7 days back the chart draws a
   * marker at the left edge (the snapshot) and a synthetic "current balance"
   * point on the right. The click sweeps a few x positions near the left edge
   * to handle small layout shifts (axis label widths, padding).
   */
  async openSnapshotEditorAt(): Promise<SnapshotEditorPage> {
    const chart = this.page.locator('[data-testid=net-worth-chart]');
    await chart.waitFor({ state: 'visible' });
    const canvas = chart.locator('canvas').first();
    const box = await canvas.boundingBox();
    if (!box) {
      throw new Error('net-worth chart canvas has no bounding box');
    }
    const editor = new SnapshotEditorPage(this.page);
    // Echarts plots the leftmost point inside the axis margin, so sweep for it.
    for (const xRatio of [0.06, 0.08, 0.04, 0.1, 0.02]) {
      await canvas.click({
        position: { x: box.width * xRatio, y: box.height * 0.4 },
      });
      try {
        await this.page.waitForURL(/\/statistics\/snapshots\/\d+/, { timeout: 2_000 });
        await editor.waitForLoaded();
        return editor;
      }
      catch {
        // Try the next x offset.
      }
    }
    throw new Error('Failed to open the snapshot editor by clicking the chart');
  }
}
