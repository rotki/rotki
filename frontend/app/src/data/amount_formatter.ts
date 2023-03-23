import { BigNumber } from '@rotki/common';

const abbreviationList = [
  [12, 'T'],
  [9, 'B'],
  [6, 'M'],
  [3, 'k']
] as const;

export class AmountFormatter {
  format(
    amount: BigNumber,
    precision: number,
    thousandSeparator: string,
    decimalSeparator: string,
    roundingMode?: BigNumber.RoundingMode,
    abbreviateNumber?: boolean
  ) {
    const usedRoundingMode =
      roundingMode === undefined ? BigNumber.ROUND_DOWN : roundingMode;

    if (abbreviateNumber) {
      const usedAbbreviation = abbreviationList.find(([digitNum, _]) =>
        amount.abs().gte((10 ** digitNum) as number)
      );

      if (usedAbbreviation) {
        return `${amount
          .dividedBy((10 ** usedAbbreviation[0]) as number)
          .toFormat(
            precision,
            usedRoundingMode,
            getBnFormat(thousandSeparator, decimalSeparator)
          )} ${usedAbbreviation[1]}`;
      }
    }

    return amount.toFormat(
      precision,
      usedRoundingMode,
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
