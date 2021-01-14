export const FETCH_LEDGER_ACTIONS = 'fetchLedgerActions' as const;

export const ACTION_INCOME = 'income';
export const ACTION_LOSS = 'loss';
export const ACTION_DONATION = 'donation received';
export const ACTION_EXPENSE = 'expense';
export const ACTION_DIVIDENDS = 'dividends income';

export const ACTION_TYPES = [
  ACTION_INCOME,
  ACTION_LOSS,
  ACTION_DONATION,
  ACTION_EXPENSE,
  ACTION_DIVIDENDS
] as const;
