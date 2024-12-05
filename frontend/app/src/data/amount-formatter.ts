import { BigNumber } from '@rotki/common';

interface BnFormat {
  groupSize: number;
  groupSeparator: string;
  decimalSeparator: string;
}

export const abbreviationList: [number, string][] = [
  [12, 'T'],
  [9, 'B'],
  [6, 'M'],
  [3, 'k'],
];

export class AmountFormatter {
  format(
    amount: BigNumber,
    precision: number,
    thousandSeparator: string,
    decimalSeparator: string,
    roundingMode?: BigNumber.RoundingMode,
    abbreviateNumber?: boolean,
  ): string {
    const usedRoundingMode = roundingMode === undefined ? BigNumber.ROUND_DOWN : roundingMode;

    if (abbreviateNumber) {
      const usedAbbreviation = abbreviationList.find(([digitNum, _]) => amount.abs().gte(10 ** digitNum));

      if (usedAbbreviation) {
        return `${amount
          .dividedBy(10 ** usedAbbreviation[0])
          .toFormat(
            precision,
            usedRoundingMode,
            getBnFormat(thousandSeparator, decimalSeparator),
          )} ${usedAbbreviation[1]}`;
      }
    }

    return amount.toFormat(precision, usedRoundingMode, getBnFormat(thousandSeparator, decimalSeparator));
  }
}

export const displayAmountFormatter = new AmountFormatter();

export function getBnFormat(thousandSeparator: string, decimalSeparator: string): BnFormat {
  return {
    decimalSeparator,
    groupSeparator: thousandSeparator,
    groupSize: 3,
  };
}
