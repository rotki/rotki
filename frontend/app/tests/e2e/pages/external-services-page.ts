import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_DIALOG, TIMEOUT_MEDIUM } from '../helpers/constants';
import { RotkiApp } from './rotki-app';

export class ExternalServicesPage {
  private lastPutBody: unknown;

  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'api-keys', 'api-keys-external-services');
    await this.page.locator('[data-cy=external-keys]').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Stubs the external-services endpoints so no real key is persisted. GET
   * starts empty; PUT captures the request body and echoes the saved key back
   * in the backend-shaped response.
   */
  async setupMocks(): Promise<void> {
    await this.page.route('**/api/1/external_services', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        await route.fulfill({
          body: JSON.stringify({ message: '', result: {} }),
          contentType: 'application/json',
          status: 200,
        });
      }
      else if (method === 'PUT') {
        this.lastPutBody = route.request().postDataJSON();
        const service = (route.request().postDataJSON()?.services ?? [])[0] ?? {};
        await route.fulfill({
          body: JSON.stringify({ message: '', result: { [service.name]: { api_key: service.api_key } } }),
          contentType: 'application/json',
          status: 200,
        });
      }
      else {
        await route.continue();
      }
    });
  }

  serviceTitle(title: string): Locator {
    return this.page.locator('[data-cy=external-keys]').getByText(title, { exact: true });
  }

  async expectServicesRendered(titles: string[]): Promise<void> {
    for (const title of titles)
      await expect(this.serviceTitle(title)).toBeVisible();
  }

  async saveEtherscanKey(key: string): Promise<void> {
    const card = this.page.locator('[data-cy=etherscan-api-keys]');
    await card.getByRole('button', { name: 'Enter API key' }).click();

    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_DIALOG });
    await dialog.locator('[data-cy=service-key__api-key] input').fill(key);
    await dialog.locator('[data-cy=confirm]').click();
  }

  async expectSaveSucceeded(key: string): Promise<void> {
    await expect
      .poll(() => JSON.stringify(this.lastPutBody ?? {}))
      .toContain(key);
    expect(JSON.stringify(this.lastPutBody)).toContain('etherscan');
    await expect(this.page.locator('[data-cy=bottom-dialog]').getByText('Successfully updated the key')).toBeVisible();
  }

  async closeDialog(): Promise<void> {
    const dialog = this.page.locator('[data-cy=bottom-dialog]');
    await dialog.locator('[data-cy=cancel]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_DIALOG });
  }
}
