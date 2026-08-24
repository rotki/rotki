import { expect, type Page } from '@playwright/test';

export class AccountSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-testid=user-menu-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-testid=settings-button]').click();
    await this.page.locator('[data-testid=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-testid="settings__account"]').click();
    await this.page.locator('[data-testid=current-password]').waitFor({ state: 'visible' });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.page.locator('[data-testid=current-password] input').clear();
    await this.page.locator('[data-testid=current-password] input').fill(currentPassword);
    await this.page.locator('[data-testid=new-password] input').clear();
    await this.page.locator('[data-testid=new-password] input').fill(newPassword);
    await this.page.locator('[data-testid=confirm-password] input').clear();
    await this.page.locator('[data-testid=confirm-password] input').fill(newPassword);
    await this.page.locator('[data-testid=change-password-button]').click();
  }

  async confirmSuccess(): Promise<void> {
    await expect(this.page.locator('[data-testid=message-dialog-title]')).toContainText('Success');
    await this.page.locator('[data-testid=message-dialog-ok]').click();
  }
}
