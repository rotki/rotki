import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';

/**
 * Drives the saved-views menu in the pill filter bar
 * (`modules/core/table/pill/PillViewsMenu.vue`).
 *
 * Its own object rather than more methods on `PillFilterBar`: a view is a stored filter set, which
 * is a different thing from the filters currently in the bar, and the two only meet at the star
 * button that opens this menu.
 */
export class PillViewsMenu {
  constructor(private readonly page: Page) {}

  private get list(): Locator {
    return this.page.locator('[data-testid=pill-views-list]');
  }

  /**
   * Opens the menu. It stays open while it is used, so the caller closes it by applying a view or
   * by pressing Escape.
   */
  async open(): Promise<void> {
    await this.page.locator('[data-testid=pill-views]').click();
    await this.list.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  /** A view's row, found by its name rather than its position, which shifts as views come and go. */
  private row(name: string): Locator {
    return this.page.locator('[data-testid=pill-views-apply]').filter({ hasText: name });
  }

  /** Names the bar's current filters and saves them as a view. Leaves the menu open. */
  async save(name: string): Promise<void> {
    await this.page.locator('[data-testid=pill-views-name]').fill(name);
    await this.page.locator('[data-testid=pill-views-save]').click();
    await expect(this.row(name)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  /** Applies a stored view, which also closes the menu. */
  async apply(name: string): Promise<void> {
    await this.row(name).click();
  }

  async remove(name: string): Promise<void> {
    const row = this.row(name);
    // The delete control is the row's sibling, so step up to the row wrapper to reach it.
    await row.locator('xpath=..').locator('[data-testid=pill-views-delete]').click();
    await expect(row).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  }

  async expectVisible(name: string): Promise<void> {
    await expect(this.row(name)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  async expectEmpty(): Promise<void> {
    await expect(this.page.locator('[data-testid=pill-views-empty]')).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  }

  /** The muted line under a view's name, saying what it filters. */
  async summary(name: string): Promise<string> {
    return (await this.row(name).innerText()).trim();
  }

  /** Whether the menu offers to save at all: with nothing filtered there is nothing to name. */
  async canSave(): Promise<boolean> {
    return this.page.locator('[data-testid=pill-views-save]').isEnabled();
  }

  /** Dismisses the menu with Escape, which is the keyboard route out of it. */
  async close(): Promise<void> {
    await this.page.keyboard.press('Escape');
    await expect(this.list).toBeHidden({ timeout: TIMEOUT_MEDIUM });
  }
}
