export const WITHDRAW = 'withdraw';
export const DEPOSIT = 'deposit';

export const YEARN_EVENTS = [WITHDRAW, DEPOSIT] as const;

const AAVE_BORROW_RATE_STABLE = 'stable';
const AAVE_BORROW_RATE_VARIABLE = 'variable';

export const AAVE_BORROW_RATE = [
  AAVE_BORROW_RATE_STABLE,
  AAVE_BORROW_RATE_VARIABLE
] as const;
