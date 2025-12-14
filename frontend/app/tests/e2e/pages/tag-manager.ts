import { expect, type Page } from '@playwright/test';
import { hexToRgbPoints } from '@rotki/common';

export class TagManager {
  constructor(private readonly page: Page) {}

  async addTag(
    parent: string,
    name: string,
    description: string,
    background?: string,
    foreground?: string,
  ): Promise<void> {
    await this.page.locator(`${parent} [data-cy=add-tag-button]`).click();
    await this.page.locator('[data-cy=tag-creator-name] input').fill(name);
    await this.page.locator('[data-cy=tag-creator-description] input').fill(description);

    if (background && foreground) {
      const bgInput = this.page.locator('[data-cy=tag-creator__color-picker__background] input');
      await bgInput.clear();
      await bgInput.fill(background);
      // Trigger update by pressing Tab to blur
      await bgInput.press('Tab');

      const bgDisplay = this.page.locator('[data-cy=tag-creator__color-picker__background] [data-cy=color-display]');
      await expect(bgDisplay).toHaveCSS('background-color', `rgb(${hexToRgbPoints(background).join(', ')})`);

      const fgInput = this.page.locator('[data-cy=tag-creator__color-picker__foreground] input');
      await fgInput.clear();
      await fgInput.fill(foreground);
      // Trigger update by pressing Tab to blur
      await fgInput.press('Tab');

      const fgDisplay = this.page.locator('[data-cy=tag-creator__color-picker__foreground] [data-cy=color-display]');
      await expect(fgDisplay).toHaveCSS('background-color', `rgb(${hexToRgbPoints(foreground).join(', ')})`);
    }

    // Use filter to get the Create Tag dialog's confirm button specifically
    const tagCreatorDialog = this.page.locator('[data-cy=bottom-dialog]').filter({ hasText: 'Create Tag' });
    await tagCreatorDialog.locator('[data-cy=confirm]').click();
    // Wait for the tag creation dialog to close
    await tagCreatorDialog.waitFor({ state: 'detached' });
  }
}
