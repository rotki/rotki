import { expect, type Page } from '@playwright/test';
import { TIMEOUT_DIALOG } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

export class ApiKeysPage {
  constructor(private readonly page: Page) {}

  async visit(submenu: string): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'api-keys', submenu);
  }

  async addExchange(apiKey: string, apiSecret: string, exchange: string, name: string): Promise<void> {
    // Set up route mocks BEFORE triggering any requests
    let capturedRequest: { api_key?: string; api_secret?: string; name?: string; location?: string } = {};

    await this.page.route('**/api/1/exchanges', async (route) => {
      if (route.request().method() === 'PUT') {
        const postData = route.request().postDataJSON();
        capturedRequest = postData;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ result: true, message: '' }),
        });
      }
      else {
        await route.continue();
      }
    });

    // Mock the balance request
    await this.page.route(`**/api/1/exchanges/balances/${exchange}**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          result: { task_id: 100001 },
          message: '',
        }),
      });
    });

    // Now open the dialog and fill the form
    await this.page.locator('[data-cy=exchanges]').locator('[data-cy=add-exchange]').click();
    const keys = this.page.locator('[data-cy=exchange-keys]');
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible', timeout: TIMEOUT_DIALOG });

    await keys.locator('[data-cy=exchange] [data-id=activator]').click();
    await keys.locator('[data-cy=exchange] input').fill(exchange);
    await expect(this.page.locator('[role=menu-content] button')).toHaveCount(1);
    await keys.locator('[data-cy=exchange] input').press('Enter');
    await keys.locator('[data-cy=name] input').fill(name);
    await keys.locator('[data-cy=api-key] input').fill(apiKey);
    await keys.locator('[data-cy=api-secret] input').fill(apiSecret);

    await this.page.locator('[data-cy=bottom-dialog]').locator('[data-cy=confirm]').click();
    await this.page.locator('[data-cy=bottom-dialog]').waitFor({ state: 'detached', timeout: TIMEOUT_DIALOG });

    // Verify the interceptor captured the correct values
    expect(capturedRequest.api_key).toBe(apiKey);
    expect(capturedRequest.api_secret).toBe(apiSecret);
    expect(capturedRequest.name).toBe(name);
    expect(capturedRequest.location).toBe(exchange);
  }

  async exchangeIsAdded(exchange: string, name: string): Promise<void> {
    const table = this.page.locator('[data-cy=exchange-table]').locator('table');
    const row = table.locator('tbody tr').first();
    await row.waitFor({ state: 'visible' });
    await expect(row.locator('td').first()).toContainText(exchange);
    await expect(row.locator('td').nth(1)).toContainText(name);
  }
}
