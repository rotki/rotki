import type { APIRequestContext, Page } from '@playwright/test';
import process from 'node:process';
import {
  apiAddEtherscanKey,
  apiCreateAccount,
  apiDisableModules,
  apiLogin,
  apiLogout,
  apiUpdateAssets,
} from '../helpers/api';
import { TIMEOUT_LONG, TIMEOUT_MEDIUM, TIMEOUT_SHORT } from '../helpers/constants';
import { confirmDialog, disableAnimations, TK } from '../helpers/utils';

export class RotkiApp {
  constructor(
    private readonly page: Page,
    private readonly request: APIRequestContext,
  ) {}

  private async loadEnv(): Promise<void> {
    const apiKey = process.env.ETHERSCAN_API_KEY || TK.join('');
    if (apiKey) {
      await apiAddEtherscanKey(this.request, apiKey);
    }
    else {
      console.warn('ETHERSCAN_API_KEY not set');
    }
  }

  async visit(): Promise<void> {
    await this.page.goto('/#/user/login?skip_update=1');
    await disableAnimations(this.page);
  }

  async createAccount(username: string, password: string = '1234'): Promise<void> {
    await apiLogout(this.request);

    // Navigate to login page first
    await this.page.goto('/#/user/login?skip_update=1', { timeout: TIMEOUT_MEDIUM });
    await disableAnimations(this.page);

    await this.page.locator('[data-cy=connection-loading__content]').waitFor({ state: 'detached' });
    await this.page.locator('[data-cy=account-management-forms]').scrollIntoViewIfNeeded();
    await this.page.locator('[data-cy=account-management-forms]').waitFor({ state: 'visible' });

    // Check if we're on the login page (accounts exist) or create page (fresh start)
    // On fresh start without any accounts, it might show create account form directly
    const newAccountButton = this.page.locator('[data-cy=new-account]');
    const introductionContinue = this.page.locator('[data-cy=create-account__introduction__continue]');

    // Wait for either the login form's "Create account" button or the create wizard's continue button
    const visibleElement = await Promise.race([
      newAccountButton.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT }).then(() => 'login'),
      introductionContinue.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT }).then(() => 'create'),
    ]).catch(() => 'login');

    // If on login page, click "Create account" button first
    if (visibleElement === 'login' && await newAccountButton.isVisible()) {
      await newAccountButton.click();
    }

    await this.page.locator('[data-cy=create-account__introduction__continue]').click();
    await this.page.locator('[data-cy=create-account__premium__button__continue]').click();
    await this.page.locator('[data-cy=create-account__fields__username] input').fill(username);
    await this.page.locator('[data-cy=create-account__fields__password] input').fill(password);
    await this.page.locator('[data-cy=create-account__fields__password-repeat] input').fill(password);
    await this.page.locator('[data-cy=create-account__boxes__user-prompted] > label').click();
    await this.page.locator('[data-cy=create-account__credentials__button__continue]').click();
    await this.page.locator('[data-cy=create-account__submit-analytics__button__continue]').click();
    await this.page.locator('[data-cy=account-management-forms]').waitFor({ state: 'detached' });
    await apiUpdateAssets(this.request);
    await this.loadEnv();
  }

  async clear(): Promise<void> {
    await this.logout();
  }

  async fasterLogin(username: string, password: string = '1234', disableModules: boolean = false): Promise<void> {
    await apiLogout(this.request);

    // Try to login first (for existing users), create account only if login fails
    const loginSuccess = await apiLogin(this.request, username, password);
    if (!loginSuccess) {
      // User doesn't exist, create account
      await apiCreateAccount(this.request, username, password);
    }

    if (disableModules) {
      await apiDisableModules(this.request);
    }

    await this.loadEnv();
    await this.visit();
    await this.login(username, password);
  }

  async checkGetPremiumButton(): Promise<void> {
    await this.page.locator('[data-cy=get-premium-button]').waitFor({ state: 'visible' });
  }

  async relogin(username: string, password: string = '1234'): Promise<void> {
    await this.clear();
    await this.login(username, password);
  }

  async login(username: string, password: string = '1234'): Promise<void> {
    const usernameField = this.page.locator('[data-cy=username-input]');
    const usernameInput = usernameField.locator('input');
    const passwordInput = this.page.locator('[data-cy=password-input] input');
    const submitButton = this.page.locator('[data-cy=login-submit]');
    const premiumButton = this.page.locator('[data-cy=get-premium-button]');

    await usernameInput.waitFor({ state: 'visible' });

    // Check if autocomplete activator exists (not rendered when VITE_TEST=true)
    const activator = usernameField.locator('[data-id=activator]');
    const hasAutocomplete = await activator.count() > 0;

    if (hasAutocomplete) {
      // Click activator to open autocomplete dropdown
      await activator.click();
      // Wait for dropdown menu to appear
      const menu = this.page.locator('[role=menu]');
      await menu.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
      await usernameInput.fill(username);
      // Wait for dropdown option and click it
      const option = menu.getByText(username, { exact: true });
      await option.waitFor({ state: 'visible', timeout: TIMEOUT_SHORT });
      await option.click();
    }
    else {
      // Simple text field mode (when VITE_TEST=true)
      await usernameInput.fill(username);
    }

    await passwordInput.fill(password);
    await submitButton.waitFor({ state: 'visible' });
    await submitButton.click();

    // Use Promise.race to wait for either:
    // 1. Asset update dialog (needs handling)
    // 2. Premium button (already logged in, no dialog)
    const updateButton = this.page.getByRole('button', { name: 'Update' });

    const result = await Promise.race([
      updateButton.waitFor({ state: 'visible', timeout: TIMEOUT_LONG / 4 }).then(() => 'update'),
      premiumButton.waitFor({ state: 'visible', timeout: TIMEOUT_LONG / 4 }).then(() => 'logged-in'),
    ]).catch(() => 'logged-in');

    if (result === 'update') {
      await updateButton.click();

      // Handle conflicts dialog if it appears - use Promise.race again
      const keepRemoteButton = this.page.getByRole('button', { name: 'Keep All Remote' });
      const conflictResult = await Promise.race([
        keepRemoteButton.waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM }).then(() => 'conflict'),
        premiumButton.waitFor({ state: 'visible', timeout: TIMEOUT_LONG }).then(() => 'done'),
      ]).catch(() => 'done');

      if (conflictResult === 'conflict') {
        await keepRemoteButton.click();
        await premiumButton.waitFor({ state: 'visible', timeout: TIMEOUT_LONG });
      }
    }
  }

  async logout(): Promise<void> {
    await this.page.locator('[data-cy=user-menu-button]').click();
    await this.page.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await this.page.locator('[data-cy=logout-button]').click();
    await confirmDialog(this.page);
    await this.page.locator('[data-cy=username-input] input').waitFor({ state: 'visible' });
  }

  async changeCurrency(currency: string): Promise<void> {
    await this.page.locator('[data-cy=currency-dropdown]').click();
    await this.page.locator(`#change-to-${currency.toLowerCase()}`).click();
  }

  async togglePrivacyMenu(show?: boolean): Promise<void> {
    const menuButton = this.page.locator('[data-cy=privacy-menu]');
    const menuContent = this.page.locator('[data-cy=privacy-menu-content]');

    if (show) {
      await menuButton.click();
      // Wait for the slider to be visible (the slider is inside the menu content)
      await this.page.locator('[data-cy=privacy-mode-dropdown__input]').waitFor({ state: 'visible' });
    }
    else {
      const isVisible = await menuContent.isVisible();
      if (isVisible) {
        await menuButton.click();
        // Wait for menu content to be hidden
        await this.page.locator('[data-cy=privacy-mode-dropdown__input]').waitFor({ state: 'hidden' });
      }
    }
  }

  async changePrivacyMode(mode: number): Promise<void> {
    await this.togglePrivacyMenu(true);
    // Mode 0 = Normal, 1 = Semi Private, 2 = Private
    // Sibling div after slider contains mode labels
    const label = this.page.locator(`[data-cy=privacy-mode-dropdown__input] + div > div:nth-child(${mode + 1})`);
    await label.waitFor({ state: 'visible' });
    await label.click();
    await this.togglePrivacyMenu();
  }

  async toggleScrambler(enable: boolean): Promise<void> {
    const input = this.page.locator('[data-cy=privacy-mode-scramble__toggle] input[type=checkbox]');
    const isChecked = await input.isChecked();

    if (enable !== isChecked) {
      await input.click({ force: true });
    }
  }

  async changeScrambleValue(multiplier: string): Promise<void> {
    await this.toggleScrambler(true);
    const input = this.page.locator('[data-cy=privacy-mode-scramble__multiplier] input');
    await input.fill(multiplier);
  }

  async changeRandomScrambleValue(): Promise<void> {
    await this.toggleScrambler(true);
    const button = this.page.locator('[data-cy=privacy-mode-scramble__random-multiplier]');
    await button.click();
  }

  async shouldHaveQueryParam(key: string, value: string): Promise<void> {
    const url = this.page.url();
    const query = new URLSearchParams(url.split('?')[1] || '');
    const actualValue = query.get(key);
    if (actualValue !== value) {
      throw new Error(`Expected query param "${key}" to be "${value}" but got "${actualValue}"`);
    }
  }

  async shouldNotHaveQueryParam(key: string): Promise<void> {
    const url = this.page.url();
    const query = new URLSearchParams(url.split('?')[1] || '');
    const actualValue = query.get(key);
    if (actualValue !== null) {
      throw new Error(`Expected query param "${key}" to not exist but got "${actualValue}"`);
    }
  }

  static async navigateTo(page: Page, menu: string, submenu?: string): Promise<void> {
    const click = async (selector: string, scroll: boolean = false): Promise<void> => {
      const element = page.locator(selector);
      if (scroll) {
        await element.scrollIntoViewIfNeeded();
        await element.waitFor({ state: 'visible' });
      }
      await element.hover();
      await element.click();
    };

    const menuSelector = `[data-cy="navigation__${menu}"]`;
    const menuElement = page.locator(menuSelector);

    // Check if the submenu wrapper exists and if it's expanded
    const submenuWrapper = menuElement.locator('[data-cy=submenu-wrapper]');
    const hasSubmenuWrapper = await submenuWrapper.count() > 0;

    if (hasSubmenuWrapper) {
      // Check if the submenu is expanded using data-expanded attribute
      const isExpanded = await submenuWrapper.getAttribute('data-expanded') === 'true';

      if (!isExpanded) {
        await click(menuSelector, true);
      }
    }
    else {
      // It's a simple menu item, just click it
      await click(menuSelector, true);
    }

    if (submenu) {
      await submenuWrapper.scrollIntoViewIfNeeded();
      await submenuWrapper.waitFor({ state: 'visible' });

      const subMenuSelector = `[data-cy="navigation__${submenu}"]`;
      await click(subMenuSelector);
    }
  }
}
