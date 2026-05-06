import type { Locator, Page } from '@playwright/test';

export class EditSnapshotDialog {
  constructor(private readonly page: Page) {}

  private get root(): Locator {
    return this.page.locator('[data-testid=edit-snapshot-dialog]');
  }

  private get bigDialog(): Locator {
    // BigDialog (`data-cy=bottom-dialog`) is the inline edit form opened from a
    // table row's edit button. It overlays the snapshot dialog itself.
    return this.page.locator('[data-cy=bottom-dialog]');
  }

  async waitForVisible(): Promise<void> {
    await this.root.waitFor({ state: 'visible' });
  }

  async editBalanceRow(asset: string, newAmount: string): Promise<void> {
    const row = this.root.locator('tr', { hasText: asset }).first();
    await row.locator('[data-cy=row-edit]').click();
    const dialog = this.bigDialog;
    await dialog.waitFor({ state: 'visible' });
    const amountInput = dialog.locator('[data-cy=amount] input');
    await amountInput.fill(newAmount);
    await this.page.locator('[data-cy=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
  }

  async editLocationRow(location: string, newUsd: string): Promise<void> {
    const row = this.root.locator('tr', { hasText: location }).first();
    await row.locator('[data-cy=row-edit]').click();
    const dialog = this.bigDialog;
    await dialog.waitFor({ state: 'visible' });
    const valueInput = dialog.locator('[data-testid=edit-location-value] input');
    await valueInput.fill(newUsd);
    await this.page.locator('[data-cy=confirm]').click();
    await dialog.waitFor({ state: 'hidden' });
  }

  async next(): Promise<void> {
    await this.page.locator('[data-testid=edit-snapshot-next]').click();
  }

  async prev(): Promise<void> {
    await this.page.locator('[data-testid=edit-snapshot-prev]').click();
  }

  async complete(): Promise<void> {
    await this.page.locator('[data-testid=edit-snapshot-complete]').click();
    await this.root.waitFor({ state: 'hidden' });
    // A "Data was successfully updated" confirmation dialog appears after a
    // successful save and otherwise sits over the dashboard, blocking the
    // next test's chart click.
    const okButton = this.page.getByRole('button', { name: 'OK', exact: true });
    try {
      await okButton.waitFor({ state: 'visible', timeout: 5_000 });
      await okButton.click();
      await okButton.waitFor({ state: 'hidden' });
    }
    catch {
      // No confirmation popped up — fine.
    }
  }
}
