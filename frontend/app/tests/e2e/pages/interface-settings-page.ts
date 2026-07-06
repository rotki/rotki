import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { confirmInlineSuccess, openSettingsTab } from '../helpers/utils';

const SECTION_IDS = ['interface_only', 'graph', 'alias', 'newly_detected_tokens', 'theme'] as const;

export class InterfaceSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await openSettingsTab(this.page, 'interface');
    await this.page.locator('#interface_only').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  async expectSectionsRendered(): Promise<void> {
    for (const id of SECTION_IDS)
      await expect(this.page.locator(`#${id}`)).toBeVisible();
  }

  async toggleAnimations(): Promise<void> {
    const control = this.page.getByTestId('animations-enabled');
    await control.scrollIntoViewIfNeeded();
    await control.locator('input').click();
    await confirmInlineSuccess(this.page, '[data-testid=animations-enabled]');
  }
}
