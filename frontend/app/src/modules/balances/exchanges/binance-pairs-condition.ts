import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import type { ConnectionRef } from '@/modules/core/common/connection';

/** The Binance account a missing-pairs condition is about. */
export interface BinanceAccount {
  /** The connection, which its market pairs are read for. */
  identifier: string;
  location: string;
  name: string;
}

/** Whether saving an exchange gave this account the market pairs it was missing. */
export function savesMissingPairs(account: BinanceAccount, form: ExchangeFormData): boolean {
  return account.identifier === form.identifier && (form.binanceMarkets?.length ?? 0) > 0;
}

/** Whether a connection is still among the connected ones, also when it was renamed since. */
export function isConnected(account: ConnectionRef, connected: readonly ConnectionRef[]): boolean {
  return connected.some(other => other.identifier === account.identifier);
}
