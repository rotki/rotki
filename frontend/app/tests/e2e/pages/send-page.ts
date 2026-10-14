import type { Locator, Page } from '@playwright/test';
import { TIMEOUT_DIALOG } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

/** The Onchain Send page: the send card, its wallet connection and its dialogs. */
export class SendPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'onchain', 'onchain-send');
    await this.connectButton.or(this.addressBadge).waitFor({ state: 'visible' });
  }

  /** The footer's connect button, the only one while disconnected. */
  get connectButton(): Locator {
    return this.page.locator('[data-testid=connect-action] button');
  }

  get modeSwitch(): Locator {
    return this.page.locator('[data-testid=wallet-mode]');
  }

  get addressBadge(): Locator {
    return this.page.locator('[data-testid=connected-address-badge]');
  }

  get untrackedStatus(): Locator {
    return this.page.locator('[data-testid=untracked-warning]');
  }

  get trackButton(): Locator {
    return this.page.locator('[data-testid=track-action]');
  }

  get error(): Locator {
    return this.page.locator('[data-testid=trade-error]');
  }

  get amountInput(): Locator {
    return this.page.locator('[data-testid=trade-amount] input');
  }

  /** The line under the amount that says when it is more than the wallet can send. */
  get amountError(): Locator {
    return this.page.locator('[data-testid=trade-amount-error]');
  }

  get sendButton(): Locator {
    return this.page.locator('[data-testid=send-action]');
  }

  get switchNetworkButton(): Locator {
    return this.page.locator('[data-testid=switch-network-action]');
  }

  get selectedBalance(): Locator {
    return this.page.locator('[data-testid=trade-asset-selected-balance]');
  }

  /** Picks an asset in the token dialog, choosing its chain there first. */
  async chooseAsset(chainName: string, asset: string): Promise<void> {
    await this.page.locator('[data-testid=trade-asset-selector]').click();
    const dialog = this.dialog();
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_DIALOG });
    await dialog.locator('[data-testid=account-blockchain-field] [data-id=activator]').click();
    await this.page.getByRole('option', { name: chainName, exact: true }).click();
    await dialog.locator(`[data-testid=trade-asset-option][data-key="${asset}"]`).click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_DIALOG });
  }

  async enterAmount(amount: string): Promise<void> {
    await this.amountInput.fill(amount);
  }

  get recipientField(): Locator {
    return this.page.locator('[data-testid=recipient-field]');
  }

  get newAddressChip(): Locator {
    return this.page.locator('[data-testid=recipient-never-interacted]');
  }

  async connect(): Promise<void> {
    await this.connectButton.click();
  }

  async disconnect(): Promise<void> {
    await this.addressBadge.click();
    await this.page.locator('[data-testid=wallet-disconnect]').click();
  }

  /** Types an address into the recipient field and leaves it, which is what takes it. */
  async enterRecipient(address: string): Promise<void> {
    const input = this.page.locator('[data-testid=recipient-search]');
    await input.click();
    await input.fill(address);
    await input.blur();
  }

  async clearRecipient(): Promise<void> {
    await this.page.locator('[data-testid=recipient-clear]').click();
  }

  dialog(): Locator {
    return this.page.locator('[role=dialog]');
  }

  async openAddressBook(): Promise<void> {
    await this.page.locator('[data-testid=recipient-open-address-book]').click();
    await this.dialog().waitFor({ state: 'visible', timeout: TIMEOUT_DIALOG });
  }

  async closeAddressBook(): Promise<void> {
    await this.page.locator('[data-testid=recipient-dialog-close]').click();
    await this.dialog().waitFor({ state: 'detached', timeout: TIMEOUT_DIALOG });
  }

  async openHistory(): Promise<void> {
    await this.page.locator('[data-testid=trade-history-open]').click();
    await this.dialog().waitFor({ state: 'visible', timeout: TIMEOUT_DIALOG });
  }

  async closeHistory(): Promise<void> {
    await this.page.locator('[data-testid=trade-history-close]').click();
    await this.dialog().waitFor({ state: 'detached', timeout: TIMEOUT_DIALOG });
  }

  /** The vertical position of an element, to assert that a message appearing did not move it. */
  async topOf(locator: Locator): Promise<number> {
    const box = await locator.boundingBox();
    if (!box)
      throw new Error('Element has no box; it is not visible');
    return Math.round(box.y);
  }
}
