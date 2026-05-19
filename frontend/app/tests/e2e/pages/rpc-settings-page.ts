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
    // Default Playwright viewport is wide enough to show the rail.
    await this.page.getByTestId('rpc-settings-rail').waitFor({ state: 'visible' });
  }

  async expectRailVisible(): Promise<void> {
    await expect(this.page.getByTestId('rpc-settings-rail')).toBeVisible();
    await expect(this.page.getByTestId('rpc-settings-dropdowns')).toHaveCount(0);
  }

  async expectDropdownFallbackVisible(): Promise<void> {
    await expect(this.page.getByTestId('rpc-settings-dropdowns')).toBeVisible();
    await expect(this.page.getByTestId('rpc-settings-rail')).toHaveCount(0);
  }

  async expectAddNodeVisible(): Promise<void> {
    await expect(this.page.getByTestId('add-node')).toBeVisible();
  }

  async expectAddNodeHidden(): Promise<void> {
    await expect(this.page.getByTestId('add-node')).toHaveCount(0);
  }

  async visitWithTab(tab: string): Promise<void> {
    await this.page.goto(`/#/settings/rpc?tab=${tab}`);
    await this.page.getByTestId('rpc-settings-rail').waitFor({ state: 'visible' });
  }

  async expectActiveTab(label: string): Promise<void> {
    const active = this.page.getByTestId('rpc-settings-rail').locator('[role="tab"][aria-selected="true"]');
    await expect(active).toHaveText(new RegExp(label));
  }

  async clickRailTab(label: string): Promise<void> {
    await this.page.getByTestId('rpc-settings-rail').locator('[role="tab"]', { hasText: label }).click();
  }

  async expectUrlTab(tab: string): Promise<void> {
    await expect(this.page).toHaveURL(new RegExp(`tab=${tab}(?:&|$)`));
  }

  async expectSolanaUnderOtherEndpoints(): Promise<void> {
    const rail = this.page.getByTestId('rpc-settings-rail');
    const groups = rail.locator('> div');
    const otherGroup = groups.nth(1);
    await expect(otherGroup).toContainText('Other endpoints');
    await expect(otherGroup).toContainText('Solana');
    const evmGroup = groups.nth(0);
    await expect(evmGroup).not.toContainText('Solana');
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
