import { expect, type Page } from '@playwright/test';
import { confirmInlineSuccess } from '../helpers/utils';

export class AccountingSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-cy=user-menu-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=settings-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-cy="settings__accounting"]').click();
    await this.page.locator('[data-cy=crypto2crypto-switch]').waitFor({ state: 'visible' });
  }

  async setTaxFreePeriodDays(value: string): Promise<void> {
    await this.page.locator('[data-cy=taxfree-period] input').clear();
    await this.page.locator('[data-cy=taxfree-period] input').fill(value);
    await this.page.locator('[data-cy=taxfree-period] input').blur();
    await confirmInlineSuccess(this.page, '[data-cy=taxfree-period] .details', value);
  }

  async changeSwitch(target: string, enabled: boolean): Promise<void> {
    await this.page.locator(target).scrollIntoViewIfNeeded();
    await this.page.locator(target).waitFor({ state: 'visible' });
    await this.verifySwitchState(target, !enabled);
    await this.page.locator(`${target} input`).click();
    await this.verifySwitchState(target, enabled);
    await confirmInlineSuccess(this.page, `${target} .details .text-rui-success`);
  }

  async verifySwitchState(target: string, enabled: boolean): Promise<void> {
    if (enabled) {
      await expect(this.page.locator(`${target} input`)).toBeChecked();
    }
    else {
      await expect(this.page.locator(`${target} input`)).not.toBeChecked();
    }
  }
}
