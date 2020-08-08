import { default as BigNumber } from 'bignumber.js';

export class AmountFormatter {
  private numberPartsRegex = /(%T.*)(%U.*)(%D)/g;
  private amountRegex = /%T.*%U.*%D/g;

  format(
    amount: BigNumber,
    format: string,
    precision: number,
    roundingMode: BigNumber.RoundingMode,
    currency?: string
  ) {
    /**
     * Get separators
     */
    const numberParts = [...format.matchAll(this.numberPartsRegex)][0];
    if (!numberParts)
      throw new Error('Missing format placeholders: %T, %U or %D');
    const thousandsSeparator = numberParts[1].substring(2);
    const decimalSeparator = numberParts[2].substring(2);

    /**
     * Format the amount using BigNumbers
     */
    const formattedAmount = amount.toFormat(
      amount.modulo(1).comparedTo(0) === 0 ? 0 : precision,
      roundingMode,
      {
        groupSize: 3,
        groupSeparator: thousandsSeparator,
        decimalSeparator
      }
    );
    return format
      .replace(this.amountRegex, formattedAmount)
      .replace(/%C/gm, currency || '')
      .trim();
  }
}

export const displayAmountFormatter = new AmountFormatter();
