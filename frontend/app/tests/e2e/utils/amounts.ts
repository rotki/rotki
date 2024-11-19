import { type BigNumber, bigNumberify } from '@rotki/common';

/**
 * Removes the separator (comma) from a given amount.
 *
 * @param {string} amount - The amount with separator.
 * @return {string} The amount without separator.
 */
export function removeSeparator(amount: string): string {
  return amount.replace(/,/g, '');
}

/**
 * Formats a given amount to use two decimal points.
 *
 * @param {string} amount - The amount to be formatted.
 * @return {string} The formatted amount.
 */
export function formatAmount(amount: string): string {
  return bigNumberify(amount).toFormat(2);
}

/**
 * Parses a given string and converts it into a BigNumber.
 * Removes and comma separator in the text.
 *
 * @param {string} text - The string to be parsed.
 * @returns {BigNumber} - The parsed BigNumber.
 */
export function parseBigNumber(text: string): BigNumber {
  return bigNumberify(removeSeparator(text));
}

/**
 * Updates the balance of a location.
 *
 * @param {string} amount - The amount to be updated.
 * @param {Map<string, BigNumber>} balances - The balances map.
 * @param {string} location - The location to update the balance for.
 *
 * @return {void} - Returns nothing.
 */
export function updateLocationBalance(amount: string, balances: Map<string, BigNumber>, location: string): void {
  const balance = parseBigNumber(amount);
  const locationBalance = balances.get(location);
  if (!locationBalance)
    balances.set(location, balance);
  else
    balances.set(location, locationBalance.plus(balance));
}
