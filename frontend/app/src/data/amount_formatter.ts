import { BigNumber } from '@rotki/common';

export class AmountFormatter {
  format(
    amount: BigNumber,
    precision: number,
    thousandSeparator: string,
    decimalSeparator: string,
    roundingMode?: BigNumber.RoundingMode
  ) {
    return amount.toFormat(
      precision,
      roundingMode === undefined ? BigNumber.ROUND_DOWN : roundingMode,
      getBnFormat(thousandSeparator, decimalSeparator)
    );
  }
}

export const displayAmountFormatter = new AmountFormatter();

export const getBnFormat = (
  thousandSeparator: string,
  decimalSeparator: string
) => ({
  groupSize: 3,
  groupSeparator: thousandSeparator,
  decimalSeparator
});
