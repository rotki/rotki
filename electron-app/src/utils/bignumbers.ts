import BigNumber from 'bignumber.js';

export function bigNumberify(value: string) {
  return new BigNumber(value);
}

export const Zero = new BigNumber(0);
