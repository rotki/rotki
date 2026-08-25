import { expect, type Page } from '@playwright/test';

export class SettingsSearchPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-testid=user-menu-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-testid=settings-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-testid=nav-tab][data-key="settings-general"]').click();
    await this.page.locator('[data-testid=settings-search]').waitFor({ state: 'visible' });
  }

  /** Types a query into the settings search and clicks the result row containing `resultText`. */
  async searchAndSelect(query: string, resultText: string): Promise<void> {
    const root = this.page.locator('[data-testid=settings-search]');
    // RuiAutoComplete keeps a zero-size input until its activator is clicked; open it first, then type.
    await root.locator('[data-id=activator]').click();
    const input = root.locator('input');
    await input.fill(query);
    const result = this.page.locator('[data-testid=settings-search-item]').filter({ hasText: resultText });
    await result.first().waitFor({ state: 'visible' });
    await result.first().click();
  }

  /** Asserts the target row scrolled into view and received the transient highlight flash. */
  async expectScrolledAndHighlighted(anchorId: string): Promise<void> {
    const target = this.page.locator(`#${anchorId}`);
    await expect(target).toBeInViewport();
    // the highlight flash briefly adds these utility classes to the target row
    await expect(target).toHaveClass(/rounded-lg/);
  }
}
