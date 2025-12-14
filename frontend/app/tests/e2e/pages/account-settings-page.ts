import { expect, type Page } from '@playwright/test';

export class AccountSettingsPage {
  constructor(private readonly page: Page) {}

  async visit(): Promise<void> {
    await this.page.locator('[data-cy=user-menu-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=settings-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'detached' });
    await this.page.locator('[data-cy="settings__account"]').click();
    await this.page.locator('[data-cy=current-password]').waitFor({ state: 'visible' });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.page.locator('[data-cy=current-password] input').clear();
    await this.page.locator('[data-cy=current-password] input').fill(currentPassword);
    await this.page.locator('[data-cy=new-password] input').clear();
    await this.page.locator('[data-cy=new-password] input').fill(newPassword);
    await this.page.locator('[data-cy=confirm-password] input').clear();
    await this.page.locator('[data-cy=confirm-password] input').fill(newPassword);
    await this.page.locator('[data-cy=change-password-button]').click();
  }

  async confirmSuccess(): Promise<void> {
    await expect(this.page.locator('[data-cy=message-dialog__title]')).toContainText('Success');
    await this.page.locator('[data-cy=message-dialog__ok]').click();
  }
}
