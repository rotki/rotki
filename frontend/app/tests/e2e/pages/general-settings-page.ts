import { expect, type Page } from '@playwright/test';
import { confirmInlineSuccess } from '../helpers/utils';
import { RotkiApp } from './rotki-app';

export class GeneralSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-testid=user-menu-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-testid=settings-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-testid="settings-general"]').click();
    await this.page.locator('[data-testid=floating-precision-settings]').waitFor({ state: 'visible' });
  }

  async setInputFieldValue(selector: string, value: string): Promise<void> {
    const input = this.page.locator(`${selector} input`);
    await input.clear();
    await input.fill(value);
    await input.blur();
  }

  async setFloatingPrecision(value: string): Promise<void> {
    await this.setInputFieldValue('[data-testid=floating-precision-settings]', value);
  }

  async changeAnonymousUsageStatistics(): Promise<void> {
    await this.page.locator('[data-testid=anonymous-usage-statistics-input]').click();
    await confirmInlineSuccess(this.page, '[data-testid=anonymous-usage-statistics-input] .details .text-rui-success');
  }

  async selectCurrency(value: string): Promise<void> {
    await this.page.locator('[data-testid=currency-selector]').click();
    await this.page.locator(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  async setBalanceSaveFrequency(value: string): Promise<void> {
    await this.setInputFieldValue('[data-testid=balance-save-frequency-input]', value);
  }

  async setDateDisplayFormat(value: string): Promise<void> {
    await this.setInputFieldValue('[data-testid=date-display-format-input]', value);
  }

  /** The input format is a menu select, not a free-text field: pick the option by its value. */
  async selectDateInputFormat(value: string): Promise<void> {
    await this.page.locator('[data-testid=date-input-format-input]').click();
    await this.page.locator('[role=menu]').getByText(value, { exact: true }).click();
  }

  async setThousandSeparator(value: string): Promise<void> {
    await this.setInputFieldValue('[data-testid=thousand-separator-input]', value);
  }

  async setDecimalSeparator(value: string): Promise<void> {
    await this.setInputFieldValue('[data-testid=decimal-separator-input]', value);
  }

  /** The messages shown under a separator field, validation or writer alike. */
  async separatorMessages(field: 'thousand' | 'decimal'): Promise<string> {
    return this.page.locator(`[data-testid=${field}-separator-input] .details`).innerText();
  }

  async separatorValues(): Promise<{ thousand: string; decimal: string }> {
    return {
      decimal: await this.page.locator('[data-testid=decimal-separator-input] input').inputValue(),
      thousand: await this.page.locator('[data-testid=thousand-separator-input] input').inputValue(),
    };
  }

  async verify(settings: {
    anonymousUsageStatistics: boolean;
    floatingPrecision: string;
    dateDisplayFormat: string;
    dateInputFormat: string;
    thousandSeparator: string;
    decimalSeparator: string;
    currencyLocation: 'after' | 'before';
    currency: string;
    balanceSaveFrequency: string;
  }): Promise<void> {
    await expect(this.page.locator('[data-testid=floating-precision-settings] input')).toHaveValue(settings.floatingPrecision);

    if (settings.anonymousUsageStatistics) {
      await expect(this.page.locator('[data-testid=anonymous-usage-statistics-input] input')).toBeChecked();
    }
    else {
      await expect(this.page.locator('[data-testid=anonymous-usage-statistics-input] input')).not.toBeChecked();
    }

    await expect(this.page.locator('[data-testid=currency-selector] input')).toHaveValue(settings.currency);
    await expect(this.page.locator('[data-testid=balance-save-frequency-input] input')).toHaveValue(settings.balanceSaveFrequency);

    await expect(this.page.locator('[data-testid=date-display-format-input] input')).toHaveValue(settings.dateDisplayFormat);
    await expect(this.page.locator('[data-testid=date-input-format-input] input')).toHaveValue(settings.dateInputFormat);
    await expect(this.page.locator('[data-testid=thousand-separator-input] input')).toHaveValue(settings.thousandSeparator);
    await expect(this.page.locator('[data-testid=decimal-separator-input] input')).toHaveValue(settings.decimalSeparator);

    await expect(this.page.locator('[data-testid=currency-location-input] input')).toHaveCount(2);
    await expect(this.page.locator('[data-testid=currency-location-input] input:checked')).toHaveValue(settings.currencyLocation);
  }

  async navigateAway(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'dashboard');
  }
}
