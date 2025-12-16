import { expect, type Page } from '@playwright/test';
import { type BigNumber, bigNumberify, getValidSelectorFromEvmAddress } from '@rotki/common';
import { TIMEOUT_MEDIUM } from './constants';

/**
 * CSS to disable all animations and transitions for faster tests.
 */
const DISABLE_ANIMATIONS_CSS = `
  *, *::before, *::after {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
  }
`;

/**
 * Disables CSS animations and transitions on the page for faster test execution.
 */
export async function disableAnimations(page: Page): Promise<void> {
  await page.addStyleTag({ content: DISABLE_ANIMATIONS_CSS });
}

/**
 * Selects an asset from an asset selector dropdown.
 */
export async function selectAsset(page: Page, element: string, value: string, id?: string): Promise<void> {
  await page.locator(`${element} [data-id="activator"]`).click();
  await page.locator(`${element} input`).fill(value);
  const identifier = getValidSelectorFromEvmAddress((id ?? value).toLocaleLowerCase());
  await page.locator(`#asset-${identifier}`).click();
}

/**
 * Removes the separator (comma) from a given amount.
 */
function removeSeparator(amount: string): string {
  return amount.replace(/,/g, '');
}

/**
 * Formats a given amount to use two decimal points.
 */
export function formatAmount(amount: string): string {
  return bigNumberify(amount).toFormat(2);
}

/**
 * Parses a given string and converts it into a BigNumber.
 * Removes any comma separators in the text.
 */
export function parseBigNumber(text: string): BigNumber {
  return bigNumberify(removeSeparator(text));
}

/**
 * Updates the balance of a location in a balances map.
 */
export function updateLocationBalance(amount: string, balances: Map<string, BigNumber>, location: string): void {
  const balance = parseBigNumber(amount);
  const locationBalance = balances.get(location);
  if (!locationBalance) {
    balances.set(location, balance);
  }
  else {
    balances.set(location, locationBalance.plus(balance));
  }
}

/**
 * Generates a unique test username.
 */
export function generateUsername(): string {
  const uuid = crypto.randomUUID();
  return `test_${uuid.substring(0, 6)}`;
}

/**
 * Confirms that an inline success message is displayed.
 * Used for settings pages that show "Setting saved" messages.
 */
export async function confirmInlineSuccess(page: Page, target: string, messageContains?: string): Promise<void> {
  const element = page.locator(target);
  await element.scrollIntoViewIfNeeded();
  await expect(element).toContainText('Setting saved', { timeout: TIMEOUT_MEDIUM });

  if (messageContains) {
    await expect(element).toContainText(messageContains);
  }
}

/**
 * Confirms a dialog by clicking the confirm button.
 * Optionally verifies the dialog title contains expected text.
 */
export async function confirmDialog(page: Page, expectedTitle?: string): Promise<void> {
  const dialog = page.locator('[data-cy=confirm-dialog]');

  if (expectedTitle) {
    await expect(dialog.locator('[data-cy=dialog-title]')).toContainText(expectedTitle);
  }

  await dialog.locator('[data-cy=button-confirm]').click();
}

/**
 * Default Etherscan API key (obfuscated).
 */
export const TK = [
  'R',
  'C',
  '8',
  'A',
  'C',
  'A',
  'F',
  'I',
  '7',
  'W',
  'Y',
  'H',
  'T',
  '7',
  '8',
  '8',
  'K',
  'M',
  '6',
  'M',
  'M',
  'U',
  'H',
  '4',
  'S',
  'X',
  'U',
  'V',
  'U',
  'V',
  'V',
  'M',
  'M',
  'R',
];
