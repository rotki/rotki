import { expect, type Page } from '@playwright/test';
import { confirmInlineSuccess } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

export class GeneralSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-cy=user-menu-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=settings-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-cy="settings__general"]').click();
    await this.page.locator('[data-cy=floating-precision-settings]').waitFor({ state: 'visible' });
  }

  async setInputFieldValue(selector: string, value: string): Promise<void> {
    const input = this.page.locator(`${selector} input`);
    await input.clear();
    await input.fill(value);
    await input.blur();
  }

  async setFloatingPrecision(value: string): Promise<void> {
    await this.setInputFieldValue('[data-cy=floating-precision-settings]', value);
  }

  async changeAnonymousUsageStatistics(): Promise<void> {
    await this.page.locator('[data-cy=anonymous-usage-statistics-input]').click();
    await confirmInlineSuccess(this.page, '[data-cy=anonymous-usage-statistics-input] .details .text-rui-success');
  }

  async selectCurrency(value: string): Promise<void> {
    await this.page.locator('[data-cy=currency-selector]').click();
    await this.page.locator(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  async setBalanceSaveFrequency(value: string): Promise<void> {
    await this.setInputFieldValue('[data-cy=balance-save-frequency-input]', value);
  }

  async setDateDisplayFormat(value: string): Promise<void> {
    await this.setInputFieldValue('[data-cy=date-display-format-input]', value);
  }

  async verify(settings: {
    anonymousUsageStatistics: boolean;
    floatingPrecision: string;
    dateDisplayFormat: string;
    thousandSeparator: string;
    decimalSeparator: string;
    currencyLocation: 'after' | 'before';
    currency: string;
    balanceSaveFrequency: string;
  }): Promise<void> {
    await expect(this.page.locator('[data-cy=floating-precision-settings] input')).toHaveValue(settings.floatingPrecision);

    if (settings.anonymousUsageStatistics) {
      await expect(this.page.locator('[data-cy=anonymous-usage-statistics-input] input')).toBeChecked();
    }
    else {
      await expect(this.page.locator('[data-cy=anonymous-usage-statistics-input] input')).not.toBeChecked();
    }

    await expect(this.page.locator('[data-cy=currency-selector] input')).toHaveValue(settings.currency);
    await expect(this.page.locator('[data-cy=balance-save-frequency-input] input')).toHaveValue(settings.balanceSaveFrequency);

    await expect(this.page.locator('[data-cy=date-display-format-input] input')).toHaveValue(settings.dateDisplayFormat);
    await expect(this.page.locator('[data-cy=thousand-separator-input] input')).toHaveValue(settings.thousandSeparator);
    await expect(this.page.locator('[data-cy=decimal-separator-input] input')).toHaveValue(settings.decimalSeparator);

    await expect(this.page.locator('[data-cy=currency-location-input] input')).toHaveCount(2);
    await expect(this.page.locator('[data-cy=currency-location-input] input:checked')).toHaveValue(settings.currencyLocation);
  }

  async navigateAway(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'dashboard');
  }
}
