import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { fromBlockchain, fromExchanges, fromManual } from '@/modules/balances/aggregation/core/sources';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/modules/core/common/defaults';

/** Every balance the app holds, as the stores report it. */
export interface BalanceInputs {
  readonly blockchain: Balances;
  readonly exchanges: ExchangeData;
  readonly manual: readonly ManualBalanceWithValue[];
}

/**
 * The sources behind one location, on-chain and manual alike.
 *
 * @remarks
 * A location identifier may be a chain alias, such as `ethereum` standing for `eth`. Where `chain`
 * resolves, the location is treated as that chain, so the balances on it surface alongside any
 * manual balance tagged with the same label. The umbrella `blockchain` location reads every chain.
 * Anything else is an exchange or another manual location.
 *
 * @param location - the trade-location identifier
 * @param inputs - the balances to read from
 * @param chain - the chain `location` is an alias for, if any
 */
export function locationSources(location: string, inputs: BalanceInputs, chain: string | undefined): AssetBalanceEntries[] {
  const manual = fromManual(inputs.manual.filter(balance => balance.location === location));

  if (location === TRADE_LOCATION_BLOCKCHAIN)
    return [fromBlockchain(inputs.blockchain), manual];

  if (chain)
    return [fromBlockchain(inputs.blockchain, { chains: [chain] }), manual];

  return [fromExchanges(inputs.exchanges, location), manual];
}
