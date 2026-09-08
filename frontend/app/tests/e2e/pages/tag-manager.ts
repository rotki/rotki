import { expect, type Page } from '@playwright/test';
import { hexToRgbPoints } from '@rotki/common';
import { RotkiApp } from './rotki-app';

async function fillTagDialog(
  page: Page,
  name: string,
  description: string,
  background?: string,
  foreground?: string,
): Promise<void> {
  await page.locator('[data-testid=tag-creator-name] input').fill(name);
  await page.locator('[data-testid=tag-creator-description] input').fill(description);

  if (background && foreground) {
    const bgInput = page.locator('[data-testid=tag-creator-color-picker-background] input');
    await bgInput.clear();
    await bgInput.fill(background);
    await bgInput.press('Tab');

    const bgDisplay = page.locator('[data-testid=tag-creator-color-picker-background] [data-id=color-display]');
    await expect(bgDisplay).toHaveCSS('background-color', `rgb(${hexToRgbPoints(background).join(', ')})`);

    const fgInput = page.locator('[data-testid=tag-creator-color-picker-foreground] input');
    await fgInput.clear();
    await fgInput.fill(foreground);
    await fgInput.press('Tab');

    const fgDisplay = page.locator('[data-testid=tag-creator-color-picker-foreground] [data-id=color-display]');
    await expect(fgDisplay).toHaveCSS('background-color', `rgb(${hexToRgbPoints(foreground).join(', ')})`);
  }
}

async function confirmTagDialog(page: Page, dialogTitle: 'Create Tag' | 'Edit Tag'): Promise<void> {
  const dialog = page.locator('[data-testid=bottom-dialog]').filter({ hasText: dialogTitle });
  await dialog.locator('[data-testid=confirm]').click();
  await dialog.waitFor({ state: 'detached' });
}

export class TagManager {
  constructor(private readonly page: Page) {}

  async addTag(
    parent: string,
    name: string,
    description: string,
    background?: string,
    foreground?: string,
  ): Promise<void> {
    await this.page.locator(`${parent} [data-testid=add-tag-button]`).click();
    await fillTagDialog(this.page, name, description, background, foreground);
    await confirmTagDialog(this.page, 'Create Tag');
  }
}

export class TagManagerPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await RotkiApp.navigateTo(this.page, 'tag-manager');
  }

  private table() {
    return this.page.getByTestId('tag-manager-table');
  }

  private rows() {
    return this.table().locator('tbody tr[data-id="row"]');
  }

  private rowFor(name: string) {
    return this.rows().filter({ hasText: name });
  }

  async createTag(
    name: string,
    description: string,
    background?: string,
    foreground?: string,
  ): Promise<void> {
    await this.page.locator('[data-testid=add-tags]').click();
    await fillTagDialog(this.page, name, description, background, foreground);
    await confirmTagDialog(this.page, 'Create Tag');
  }

  async expectTagVisible(name: string): Promise<void> {
    await expect(this.rowFor(name)).toBeVisible();
  }

  async editTag(name: string, newDescription: string): Promise<void> {
    await this.rowFor(name).locator('[data-testid=row-edit]').click();
    await this.page.locator('[data-testid=tag-creator-description] input').fill(newDescription);
    await confirmTagDialog(this.page, 'Edit Tag');
    await expect(this.rowFor(name)).toContainText(newDescription);
  }

  async deleteTag(name: string): Promise<void> {
    await this.rowFor(name).locator('[data-testid=row-delete]').click();
    const confirm = this.page.locator('[data-testid=confirm-dialog]');
    await confirm.locator('[data-testid=button-confirm]').click();
    await expect(this.rowFor(name)).toHaveCount(0);
  }

  async search(query: string): Promise<void> {
    await this.page.getByTestId('tag-manager-search').locator('input').fill(query);
  }

  async clearSearch(): Promise<void> {
    await this.search('');
  }

  /**
   * Waits for the table to settle on a row count.
   *
   * @remarks
   * Searching and creating both redraw the table asynchronously, so the count has to be polled for
   * rather than read once off whatever is rendered when the assertion runs.
   */
  async expectVisibleRowCount(expected: number): Promise<void> {
    await expect(this.rows()).toHaveCount(expected);
  }

  /** For a page whose size is bounded from below but not pinned, such as the last page. */
  async expectAtLeastVisibleRows(expected: number): Promise<void> {
    await expect.poll(async () => this.rows().count()).toBeGreaterThanOrEqual(expected);
  }

  async goToNextPage(): Promise<void> {
    await this.table().locator('[data-id=table-pagination-next]').first().click();
  }

  async expectNextPageEnabled(enabled: boolean): Promise<void> {
    const next = this.table().locator('[data-id=table-pagination-next]').first();
    if (enabled)
      await expect(next).toBeEnabled();
    else
      await expect(next).toBeDisabled();
  }
}
