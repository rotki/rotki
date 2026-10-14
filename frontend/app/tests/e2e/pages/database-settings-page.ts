import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { openSettingsTab } from '../helpers/utils';

const SECTION_IDS = ['database_info', 'user_backups', 'asset_database', 'manage_data'] as const;

export class DatabaseSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await openSettingsTab(this.page, 'database');
    // The manage-data section carries the one stable testid on this page.
    await this.page.getByTestId('purge-source').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async expectSectionsRendered(): Promise<void> {
    for (const id of SECTION_IDS)
      await expect(this.page.locator(`#${id}`)).toBeVisible();
  }
}
