import type { ExchangeFormData } from '@/modules/balances/types/exchanges';

/** The Binance account a missing-pairs condition is about. */
export interface BinanceAccount {
  /** The connection, which its market pairs are read for. */
  identifier: string;
  location: string;
  name: string;
}

interface NamedAccount {
  location: string;
  name: string;
}

function isSameAccount(account: NamedAccount, other: NamedAccount): boolean {
  return account.location === other.location && account.name === other.name;
}

/** Whether saving an exchange gave this account the market pairs it was missing. */
export function savesMissingPairs(account: BinanceAccount, form: ExchangeFormData): boolean {
  return account.identifier === form.identifier && (form.binanceMarkets?.length ?? 0) > 0;
}

/** Whether a connection is still among the connected ones, also when it was renamed since. */
export function isConnectedConnection(account: { identifier: string }, connected: readonly { identifier: string }[]): boolean {
  return connected.some(other => other.identifier === account.identifier);
}

/**
 * Whether an account is still connected.
 *
 * @remarks
 * A removed or renamed account no longer is. A renamed one still without pairs is reported again
 * under its new name by the next history query.
 */
export function isConnected(account: NamedAccount, connected: readonly NamedAccount[]): boolean {
  return connected.some(other => isSameAccount(account, other));
}
