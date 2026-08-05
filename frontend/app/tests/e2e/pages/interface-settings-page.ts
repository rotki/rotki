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

  /**
   * The explorer field. Its save button is a sibling of the field rather than a child, so it is
   * reached relative to the field instead of carrying a test id of its own.
   */
  private explorer(field: 'address' | 'tx' | 'block' | 'token') {
    const input = this.page.locator(`[data-testid=explorer-${field}-input]`);
    return {
      input,
      messages: input.locator('.details'),
      save: input.locator('xpath=following-sibling::button'),
      textbox: input.locator('input'),
    };
  }

  async setExplorerUrl(field: 'address' | 'tx' | 'block' | 'token', url: string): Promise<void> {
    const { textbox } = this.explorer(field);
    await textbox.scrollIntoViewIfNeeded();
    await textbox.clear();
    await textbox.fill(url);
    await textbox.blur();
  }

  async saveExplorerUrl(field: 'address' | 'tx' | 'block' | 'token'): Promise<void> {
    await this.explorer(field).save.click();
  }

  async explorerMessages(field: 'address' | 'tx' | 'block' | 'token'): Promise<string> {
    return this.explorer(field).messages.innerText();
  }

  async explorerSaveDisabled(field: 'address' | 'tx' | 'block' | 'token'): Promise<boolean> {
    return this.explorer(field).save.isDisabled();
  }

  async explorerValue(field: 'address' | 'tx' | 'block' | 'token'): Promise<string> {
    return this.explorer(field).textbox.inputValue();
  }

  async toggleAnimations(): Promise<void> {
    const control = this.page.getByTestId('animations-enabled');
    await control.scrollIntoViewIfNeeded();
    await control.locator('input').click();
    await confirmInlineSuccess(this.page, '[data-testid=animations-enabled]');
  }
}
