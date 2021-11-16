import { BigNumber } from '@rotki/common';

export function bigNumberify(value: string | number) {
  return new BigNumber(value);
}

export const Zero = new BigNumber(0);
