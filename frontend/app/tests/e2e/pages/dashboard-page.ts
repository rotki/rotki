import { expect, type Page } from '@playwright/test';
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

  async getOverallBalance(): Promise<BigNumber> {
    const amountText = await this.page
      .locator('[data-cy=overall-balances__net-worth] [data-cy=display-amount]')
      .textContent();
    return parseBigNumber(amountText ?? '0');
  }

  async getBlockchainBalances(): Promise<Map<string, BigNumber>> {
    await this.page.locator('[data-cy=blockchain-balances]').waitFor({ state: 'visible' });

    const balances = new Map<string, BigNumber>();
    const elements = this.page.locator('[data-cy=blockchain-balance__summary]');
    const count = await elements.count();

    for (let i = 0; i < count; i++) {
      const element = elements.nth(i);
      const location = await element.getAttribute('data-location');
      if (!location)
        continue;

      const amountText = await element.locator('[data-cy=display-amount]').textContent();
      updateLocationBalance(amountText ?? '0', balances, location);
    }

    return balances;
  }

  async getNonFungibleBalances(): Promise<BigNumber> {
    const nftTable = this.page.locator('[data-cy=nft-balance-table]');
    const nftTableExists = (await nftTable.count()) > 0;

    if (!nftTableExists) {
      return Zero;
    }

    const displayAmount = nftTable.locator('tbody tr:last-child td:nth-child(2) [data-cy=display-amount]');
    const displayAmountExists = (await displayAmount.count()) > 0;

    if (!displayAmountExists) {
      return Zero;
    }

    const amountText = await displayAmount.textContent();
    return parseBigNumber(amountText ?? '0');
  }

  async getLocationBalances(): Promise<Map<string, BigNumber>> {
    await this.page.locator('[data-cy=manual-balances]').first().waitFor({ state: 'visible' });

    const balances = new Map<string, BigNumber>();
    const elements = this.page.locator('[data-cy=manual-balance__summary]');
    const count = await elements.count();

    for (let i = 0; i < count; i++) {
      const element = elements.nth(i);
      const location = await element.getAttribute('data-location');
      if (!location)
        continue;

      const amountText = await element.locator('[data-cy=display-amount]').textContent();
      updateLocationBalance(amountText ?? '0', balances, location);
    }

    return balances;
  }

  async amountDisplayIsBlurred(): Promise<void> {
    const amountDisplay = this.page.locator('[data-cy=amount-display]').first();
    const filter = await amountDisplay.evaluate(el => getComputedStyle(el).filter);
    expect(filter).toMatch(/^blur/);
  }

  async amountDisplayIsNotBlurred(): Promise<void> {
    const amountDisplay = this.page.locator('[data-cy=amount-display]').first();
    const filter = await amountDisplay.evaluate(el => getComputedStyle(el).filter);
    expect(filter).not.toMatch(/^blur/);
  }

  async percentageDisplayIsBlurred(): Promise<void> {
    await expect(this.page.locator('[data-cy=percentage-display]').first()).toHaveClass(/blur/);
  }

  async percentageDisplayIsNotBlurred(): Promise<void> {
    await expect(this.page.locator('[data-cy=percentage-display]').first()).not.toHaveClass(/blur/);
  }

  async openSnapshotMenu(): Promise<void> {
    await this.page.locator('[data-testid=snapshot-action]').click();
  }

  async openImportSnapshotDialog(): Promise<SnapshotImportDialog> {
    // The snapshot menu must already be open; the Import button lives inside it.
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
    // Echarts plots the leftmost data point a bit inside the axis margin;
    // sweep through a handful of x positions until the page navigates.
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
