import { expect, type Page } from '@playwright/test';
import { RotkiApp } from './rotki-app';

export class RpcSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-cy=user-menu-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=settings-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-cy="settings__rpc"]').click();
    await this.page.locator('[data-cy=add-node]').waitFor({ state: 'visible' });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.page.locator('[data-cy=current-password-input] input').clear();
    await this.page.locator('[data-cy=current-password-input] input').fill(currentPassword);
    await this.page.locator('[data-cy=new-password-input] input').clear();
    await this.page.locator('[data-cy=new-password-input] input').fill(newPassword);
    await this.page.locator('[data-cy=confirm-password-input] input').clear();
    await this.page.locator('[data-cy=confirm-password-input] input').fill(newPassword);
    await this.page.locator('[data-cy=change-password-button]').click();
  }

  async navigateAway(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'dashboard');
  }

  async addEthereumRPC(name: string, endpoint: string): Promise<void> {
    const addButton = this.page.locator('[data-cy=add-node]');
    await addButton.scrollIntoViewIfNeeded();
    await addButton.waitFor({ state: 'visible' });
    await addButton.click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=node-name] input').fill(name);
    await this.page.locator('[data-cy=node-endpoint] input').fill(endpoint);
    await this.page.locator('[data-cy=confirm]').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'detached' });
  }

  async confirmRPCAddition(name: string, endpoint: string): Promise<void> {
    // Use filter to find the specific node row
    const nodeRow = this.page.locator('[data-cy=ethereum-node]').filter({ hasText: name });
    await expect(nodeRow).toBeVisible();
    await expect(nodeRow).toContainText(endpoint);
  }

  async confirmRPCmissing(name: string, _endpoint: string): Promise<void> {
    // Check that no node row contains the name
    const nodeRow = this.page.locator('[data-cy=ethereum-node]').filter({ hasText: name });
    await expect(nodeRow).toHaveCount(0);
  }
}
