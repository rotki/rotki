import { expect, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';
import { openSettingsTab } from '../helpers/utils';

export class ModulesSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await openSettingsTab(this.page, 'modules');
    await this.moduleSwitch('makerdao_dsr').waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
  }

  private moduleSwitch(identifier: string) {
    return this.page.locator(`[data-testid=module-switch][data-key="${identifier}"]`);
  }

  private moduleCheckbox(identifier: string) {
    return this.moduleSwitch(identifier).locator('input');
  }

  async isModuleEnabled(identifier: string): Promise<boolean> {
    return this.moduleCheckbox(identifier).isChecked();
  }

  async toggleModule(identifier: string): Promise<void> {
    const before = await this.isModuleEnabled(identifier);
    await this.moduleSwitch(identifier).click();
    await expect(this.moduleCheckbox(identifier)).toBeChecked({ checked: !before });
  }

  async expectModuleEnabled(identifier: string, enabled: boolean): Promise<void> {
    await expect(this.moduleCheckbox(identifier)).toBeChecked({ checked: enabled });
  }

  async enableAll(): Promise<void> {
    await this.page.locator('[data-testid=modules_enable_all]').click();
  }
}
