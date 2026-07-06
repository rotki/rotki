import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { confirmInlineSuccess, openSettingsTab } from '../helpers/utils';

export class OracleSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await openSettingsTab(this.page, 'oracle');
    await this.page.locator('#price_oracle').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async expectSectionsRendered(): Promise<void> {
    await expect(this.page.locator('#price_oracle')).toBeVisible();
    await expect(this.page.locator('#penalty')).toBeVisible();
  }

  async setPenaltyDuration(value: string): Promise<void> {
    const input = this.page.getByTestId('oracle-penalty-duration').locator('input');
    await input.scrollIntoViewIfNeeded();
    await input.fill(value);
    await input.blur();
    await confirmInlineSuccess(this.page, '[data-testid=oracle-penalty-duration]');
  }

  async expectPenaltyDuration(value: string): Promise<void> {
    await expect(this.page.getByTestId('oracle-penalty-duration').locator('input')).toHaveValue(value);
  }
}
