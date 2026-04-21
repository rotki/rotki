import { expect, type Page } from '@playwright/test';
import { confirmInlineSuccess } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

export class EvmSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-cy=user-menu-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=settings-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-cy="settings__evm"]').click();
    await this.page.locator('[data-cy=chains-to-skip-detection]').waitFor({ state: 'visible' });
  }

  async navigateAway(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'dashboard');
  }

  // Indexer Order Settings
  getIndexerOrderSection() {
    return this.page.locator('[data-cy=indexer-order-setting]');
  }

  async clickAddChainButton(): Promise<void> {
    await this.page.locator('[data-cy=add-chain-button]').click();
  }

  async isAddChainButtonDisabled(): Promise<boolean> {
    return this.page.locator('[data-cy=add-chain-button]').isDisabled();
  }

  async selectChainFromMenu(chainId: string): Promise<void> {
    await this.page.locator('[data-cy=chain-menu]').waitFor({ state: 'visible' });
    await this.page.locator(`[data-cy=chain-menu-item-${chainId}]`).click();
  }

  async addChain(chainId: string): Promise<void> {
    await this.clickAddChainButton();
    await this.selectChainFromMenu(chainId);
  }

  async removeChain(chainId: string): Promise<void> {
    await this.page.locator(`[data-cy=remove-chain-${chainId}]`).click();
  }

  async selectTab(tabId: string): Promise<void> {
    await this.page.locator(`[data-cy=indexer-tab-${tabId}]`).click();
  }

  async verifyTabExists(tabId: string): Promise<void> {
    await expect(this.page.locator(`[data-cy=indexer-tab-${tabId}]`)).toBeAttached();
  }

  async verifyTabNotExists(tabId: string): Promise<void> {
    await expect(this.page.locator(`[data-cy=indexer-tab-${tabId}]`)).not.toBeAttached();
  }

  // Chains to Skip Detection Settings
  async selectChainToIgnore(value: string, waitForMessageToDisappear: boolean = true): Promise<void> {
    const field = this.page.locator('[data-cy=chains-to-skip-detection]');
    const menu = this.page.locator('[role=menu]');
    if (!await menu.isVisible()) {
      await field.locator('[data-id=activator]').click();
      await menu.waitFor({ state: 'visible' });
    }
    // Click the menu option button that contains the target chain id
    const menuOption = menu.locator(`button:has([data-value="${value}"])`).first();
    await menuOption.scrollIntoViewIfNeeded();
    await menuOption.click();
    await expect(field.locator(`[data-value=${value}]`).first()).toBeAttached();

    // Always wait for the success message to appear
    await confirmInlineSuccess(
      this.page,
      '[data-cy=chains-to-skip-detection] .details',
      'EVM Chains for which to skip automatic token detection saved successfully',
    );

    // Only wait for message to disappear on the last chain
    if (waitForMessageToDisappear) {
      await expect(this.page.locator('[data-cy=chains-to-skip-detection] .details')).toBeEmpty();
    }
  }

  async verifySkipped(entries: string[]): Promise<void> {
    for (const item of entries) {
      // Use .first() since the selector may match both chip and dropdown option
      await expect(this.page.locator(`[data-cy=chains-to-skip-detection] [data-value=${item}]`).first()).toBeAttached();
    }
  }
}
