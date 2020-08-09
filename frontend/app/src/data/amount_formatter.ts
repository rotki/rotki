import { default as BigNumber } from 'bignumber.js';

export class AmountFormatter {
  private numberPartsRegex = /(%T.*)(%U.*)(%D)/g;
  private amountRegex = /%T.*%U.*%D/g;

  format(
    amount: BigNumber,
    precision: number,
    thousandSeparator: string,
    decimalSeparator: string,
    roundingMode?: BigNumber.RoundingMode
  ) {
    return amount.toFormat(
      precision,
      roundingMode == undefined ? BigNumber.ROUND_DOWN : roundingMode,
      {
        groupSize: 3,
        groupSeparator: thousandSeparator,
        decimalSeparator
      }
    );
  }
}

export const displayAmountFormatter = new AmountFormatter();
