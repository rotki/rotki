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

  balancesCard(): Locator {
    return this.page.locator('[data-testid=bank-balances-card]');
  }

  dashboardCard(): Locator {
    return this.page.locator('[data-testid=bank-balances]');
  }
}
