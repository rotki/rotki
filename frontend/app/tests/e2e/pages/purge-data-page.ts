import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';

type PurgeSourceLabel = 'Centralized Exchange' | 'Decentralized Exchange' | 'DeFi Module' | 'Transactions';

type CexCategoryLabel = 'All' | 'Trades' | 'Deposits / Withdrawals' | 'Other events';

export class PurgeDataPage {
  constructor(private readonly page: Page) {}

  /**
   * Reaches the purge-data settings through the user menu.
   *
   * @remarks
   * Clicked through rather than navigated to. Going straight to the route lands on a blank shell,
   * because the layout never bootstraps.
   */
  async visit(): Promise<void> {
    await this.page.locator('[data-testid=user-menu-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-testid=settings-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-testid=nav-tab][data-key="settings-database"]').click();
    await this.page.getByTestId('purge-source').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Picks an option out of a `RuiAutoComplete`-backed control.
   *
   * @remarks
   * A short list renders every option up front; a long or debounced one renders the wanted option
   * only once the query narrows it, so a miss means "type to filter" rather than "give up". Both
   * routes end on the same exact-text option: clicking the first rendered one instead would pick a
   * different option whenever the search was merely slow, and the purge would run on the wrong
   * source.
   */
  private async selectOption(testId: string, text: string): Promise<void> {
    const select = this.page.getByTestId(testId);
    await select.click();
    const menu = this.page.locator('[role="listbox"], [role="menu"]').last();
    await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });

    const byText = menu.getByText(text, { exact: true }).first();
    try {
      await byText.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
    }
    catch {
      await this.page.keyboard.type(text);
      await byText.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    }
    await byText.click();
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
    const dialog = this.page.locator('[data-testid=confirm-dialog]');
    await dialog.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await dialog.locator('[data-testid=button-confirm]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
    // The success indicator is what tells later assertions the purge has landed.
    await expect(this.page.getByText('Data was successfully deleted')).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async purgeExchange(location: string, category: CexCategoryLabel): Promise<void> {
    await this.chooseSource('Centralized Exchange');
    await this.chooseExchange(location);
    await this.chooseCategory(category);
    await this.submitAndConfirm();
  }
}
