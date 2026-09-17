import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_DIALOG, TIMEOUT_MEDIUM } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

/** The bank surfaces: the connections page under API keys, the bank balances page and the dashboard card. */
export class BanksPage {
  constructor(private readonly page: Page) {}

  async visitConnections(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'api-keys', 'api-keys-banks');
    await this.page.locator('[data-testid=bank-table]').waitFor({ state: 'visible' });
  }

  async visitBalances(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'balances', 'balances-banks');
  }

  connectionRow(name: string): Locator {
    return this.page.locator('[data-testid=bank-table] tbody tr').filter({ hasText: name });
  }

  async openAddDialog(): Promise<void> {
    await this.page.locator('[data-testid=add-bank]').click();
    await this.dialog().waitFor({ state: 'visible', timeout: TIMEOUT_DIALOG });
    await this.page.locator('[data-testid=bank-connection-form]').waitFor({ state: 'visible' });
  }

  async fillConnection(name: string, login: string, secret: string): Promise<void> {
    await this.page.locator('[data-testid=bank-connection-name] input').fill(name);
    await this.page.locator('[data-testid=bank-connection-secret-api_key] input').fill(login);
    await this.page.locator('[data-testid=bank-connection-secret-api_secret] input').fill(secret);
  }

  async save(): Promise<void> {
    await this.dialog().locator('[data-testid=confirm]').click();
  }

  async saveAndClose(): Promise<void> {
    await this.save();
    await this.dialog().waitFor({ state: 'detached', timeout: TIMEOUT_DIALOG });
  }

  async cancel(): Promise<void> {
    await this.dialog().locator('[data-testid=cancel]').click();
    await this.dialog().waitFor({ state: 'detached', timeout: TIMEOUT_DIALOG });
  }

  dialog(): Locator {
    return this.page.locator('[data-testid=bottom-dialog]');
  }

  async expectMessage(text: string): Promise<void> {
    await expect(this.page.locator('[data-testid=message-dialog-description]')).toContainText(text, { timeout: TIMEOUT_MEDIUM });
  }

  async dismissMessage(): Promise<void> {
    await this.page.locator('[data-testid=message-dialog-ok]').click();
  }

  async syncConnection(name: string): Promise<void> {
    await this.connectionRow(name).locator('[data-testid=bank-sync]').click();
  }

  /** Follows the "Authenticate" action of the notification a sync paused for a TAN raises. */
  async authenticateFromNotification(): Promise<void> {
    const notification = this.page.locator('[data-id=notification]').filter({ hasText: 'Bank authentication required' });
    await notification.getByRole('button', { name: 'Authenticate' }).click({ timeout: TIMEOUT_MEDIUM });
  }

  async answerTan(tan: string): Promise<void> {
    await this.dialog().locator('[data-testid=bank-auth-response] input').fill(tan);
    await this.save();
  }

  balancesCard(): Locator {
    return this.page.locator('[data-testid=bank-balances-card]');
  }

  /** The dashboard's locations card, which holds a tile per place a balance is held. */
  dashboardCard(): Locator {
    return this.page.locator('[data-testid=dashboard-locations]');
  }

  async visitHistory(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'history');
  }

  /**
   * Opens the Banks tab of the history refresh menu.
   *
   * @remarks
   * The toggle stays disabled while the history page's own refresh runs, so waiting for it to enable
   * is also the gate that nothing from that refresh is still being sent.
   */
  async openRefreshMenuBanks(): Promise<void> {
    const toggle = this.page.locator('[data-testid=refresh-selection-toggle]');
    await expect(toggle).toBeEnabled({ timeout: TIMEOUT_DIALOG });
    await toggle.click();
    await this.page.getByRole('tab', { name: 'Banks' }).click();
  }

  async refreshPickedBank(name: string): Promise<void> {
    await this.page.locator('[data-testid=refresh-bank-row]').filter({ hasText: name }).click();
    await this.page.locator('[data-testid=refresh-selection-refresh]').click();
  }

  /**
   * Waits for the refresh the menu started to run and finish.
   *
   * @remarks
   * Bank syncs run one connection at a time, so the requests arrive one by one. Reading them before
   * the refresh settles sees only the first, which matches a single pick even when every connection
   * is being synced. The toggle is disabled while the refresh runs, so disabled then enabled again
   * is the settle signal; waiting for enabled alone could pass before the refresh starts.
   */
  async waitForRefreshSettled(): Promise<void> {
    const toggle = this.page.locator('[data-testid=refresh-selection-toggle]');
    await expect(toggle).toBeDisabled({ timeout: TIMEOUT_MEDIUM });
    await expect(toggle).toBeEnabled({ timeout: TIMEOUT_DIALOG });
  }
}
