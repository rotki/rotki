import type { ExchangeFormData } from '@/modules/balances/types/exchanges';

/** The Binance account a missing-pairs condition is about. */
export interface BinanceAccount {
  location: string;
  name: string;
}

function isSameAccount(account: BinanceAccount, other: BinanceAccount): boolean {
  return account.location === other.location && account.name === other.name;
}

/** Whether saving an exchange gave this account the market pairs it was missing. */
export function savesMissingPairs(account: BinanceAccount, form: ExchangeFormData): boolean {
  return isSameAccount(account, form) && (form.binanceMarkets?.length ?? 0) > 0;
}

/**
 * Whether an account is still connected.
 *
 * @remarks
 * A removed or renamed account no longer is. A renamed one still without pairs is reported again
 * under its new name by the next history query.
 */
export function isConnected(account: BinanceAccount, connected: readonly BinanceAccount[]): boolean {
  return connected.some(other => isSameAccount(account, other));
}
