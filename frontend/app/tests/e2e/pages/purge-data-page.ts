import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';

type PurgeSourceLabel = 'Centralized Exchange' | 'Decentralized Exchange' | 'DeFi Module' | 'Transactions';

type CexCategoryLabel = 'All' | 'Trades' | 'Deposits / Withdrawals' | 'Other events';

export class PurgeDataPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    // Reuse the same user-menu → settings → tab path the rest of the e2e suite
    // uses; navigating directly to `/#/settings/database` lands on a blank
    // shell because the layout's data-bootstrapping never runs.
    await this.page.locator('[data-cy=user-menu-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=settings-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-cy=settings__database]').click();
    await this.page.getByTestId('purge-source').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Picks an option from a `RuiAutoComplete`-backed control identified by its
   * test id. Selection-by-id (`#item-<key>`) is preferred for stability;
   * if the option for the typed text isn't rendered yet (debounced search,
   * lazy lists, etc.) we fall back to typing then clicking the first match.
   */
  private async selectOption(testId: string, text: string): Promise<void> {
    const select = this.page.getByTestId(testId);
    await select.click();
    const menu = this.page.locator('[role="listbox"], [role="menu"]').last();
    await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });

    const byText = menu.getByText(text, { exact: true }).first();
    try {
      await byText.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
      await byText.click();
    }
    catch {
      await this.page.keyboard.type(text);
      const firstOption = menu.locator('button[type="button"]').first();
      await firstOption.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
      await firstOption.click();
    }
    await menu.waitFor({ state: 'hidden', timeout: TIMEOUT_SHORT });
  }

  async chooseSource(label: PurgeSourceLabel): Promise<void> {
    await this.selectOption('purge-source', label);
  }

  async chooseExchange(location: string): Promise<void> {
    await this.selectOption('purge-cex-location', location);
  }

  async chooseCategory(label: CexCategoryLabel): Promise<void> {
    await this.selectOption('purge-cex-data-type', label);
  }

  async submitAndConfirm(): Promise<void> {
    await this.page.getByTestId('purge-submit').click();
    const dialog = this.page.locator('[data-cy=confirm-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await dialog.locator('[data-cy=button-confirm]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
    // The component shows an inline ActionStatusIndicator on success; wait for
    // the success state so subsequent assertions see the post-purge DB state.
    await expect(this.page.getByText('Data was successfully deleted')).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async purgeExchange(location: string, category: CexCategoryLabel): Promise<void> {
    await this.chooseSource('Centralized Exchange');
    await this.chooseExchange(location);
    await this.chooseCategory(category);
    await this.submitAndConfirm();
  }
}
