import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { confirmInlineSuccess, openSettingsTab } from '../helpers/utils';

const SECTION_IDS = ['interface_only', 'graph', 'alias', 'newly_detected_tokens', 'theme'] as const;

type ExplorerField = 'address' | 'tx' | 'block' | 'token';

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
  private explorer(field: ExplorerField) {
    const input = this.page.locator(`[data-testid=explorer-${field}-input]`);
    return {
      input,
      messages: input.locator('.details'),
      save: input.locator('xpath=following-sibling::button'),
      textbox: input.locator('input'),
    };
  }

  async setExplorerUrl(field: ExplorerField, url: string): Promise<void> {
    const { textbox } = this.explorer(field);
    await textbox.scrollIntoViewIfNeeded();
    await textbox.clear();
    await textbox.fill(url);
    await textbox.blur();
  }

  async saveExplorerUrl(field: ExplorerField): Promise<void> {
    await this.explorer(field).save.click();
  }

  /**
   * Validation runs off the field's own reactivity, a tick or more after `blur` returns, so every
   * assertion here has to poll rather than sample the DOM once.
   */
  async expectExplorerMessage(field: ExplorerField, text: string): Promise<void> {
    await expect(this.explorer(field).messages).toContainText(text);
  }

  /** For a rule whose wording is not what the test is pinning: some complaint, not a specific one. */
  async expectExplorerRejected(field: ExplorerField): Promise<void> {
    await expect(this.explorer(field).messages).not.toBeEmpty();
  }

  async expectSaveDisabled(field: ExplorerField): Promise<void> {
    await expect(this.explorer(field).save).toBeDisabled();
  }

  async expectSaveEnabled(field: ExplorerField): Promise<void> {
    await expect(this.explorer(field).save).toBeEnabled();
  }

  async expectExplorerValue(field: ExplorerField, url: string): Promise<void> {
    await expect(this.explorer(field).textbox).toHaveValue(url);
  }

  async toggleAnimations(): Promise<void> {
    const control = this.page.getByTestId('animations-enabled');
    await control.scrollIntoViewIfNeeded();
    await control.locator('input').click();
    await confirmInlineSuccess(this.page, '[data-testid=animations-enabled]');
  }
}
