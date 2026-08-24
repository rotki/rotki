import { type BigNumber, bigNumberify, isValidEthAddress, Zero } from '@rotki/common';

/** The amount the user asked to send is more than the balance left after gas. */
export function isAmountExceeded(amount: string, max: string): boolean {
  return bigNumberify(amount, Zero).gt(bigNumberify(max, Zero));
}

/** A send is only allowed for a positive amount to a well-formed address within the max. */
export function isTradeValid(amount: string, toAddress: string, max: string): boolean {
  const positive = bigNumberify(amount, Zero).gt(0);
  const recipientValid = !!toAddress && isValidEthAddress(toAddress);
  return positive && recipientValid && !isAmountExceeded(amount, max);
}

/**
 * What is left to send once the estimated gas is set aside. Without a known balance there is
 * nothing to offer, so the max collapses to zero rather than to the balance.
 */
export function maxSendableAmount(balance: BigNumber | undefined, estimatedGasFee: string): string {
  if (!balance)
    return '0';

  return balance.minus(estimatedGasFee).toFixed();
}
