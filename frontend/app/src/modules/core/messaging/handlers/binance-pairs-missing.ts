import type { StateHandler } from '../interfaces';
import type { BinancePairsMissingData } from '@/modules/core/messaging/types';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Records a Binance account whose trades cannot be imported because it has no market pairs
 * selected, which the action center lists.
 *
 * @remarks
 * Creates no notification. The backend repeats the report on every trade history query, and a
 * repeat replaces the account's condition rather than adding another.
 */
export function createBinancePairsMissingHandler(): StateHandler<BinancePairsMissingData> {
  const { raise } = useRaisedConditionsStore();

  return createStateHandler<BinancePairsMissingData>(({ location, name }) => {
    raise({ kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, location, name });
  });
}
