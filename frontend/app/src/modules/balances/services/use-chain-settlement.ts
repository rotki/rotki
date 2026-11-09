import type { BlockchainBalances, BtcBalances } from '@/modules/balances/types/blockchain-balances';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { convertBtcBalances } from '@/modules/accounts/core/bitcoin-accounts';
import { chainBalancesActivity } from '@/modules/balances/balances.activity';
import { ChainResultDecision, decideChainResult } from '@/modules/balances/refresh/core/chain-result';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';
import { byChainKey } from '@/modules/core/common/chains';
import { logger } from '@/modules/core/common/logging/logging';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface ChainSettlementOptions {
  /** The result covers only some of the chain's addresses. */
  readonly isTargeted?: boolean;
  /** Runs when the balances were written, as opposed to refused or dropped. */
  readonly onApplied?: () => void;
  /** A network result was applied to the chain while this result was in flight. */
  readonly overtaken?: boolean;
}

interface UseChainSettlementReturn {
  settleChain: (blockchain: string, result: Result<BlockchainBalances, TaskError>, options?: ChainSettlementOptions) => Result<void, TaskError>;
}

function isBtcBalances(data?: BtcBalances | any): data is BtcBalances {
  return !!data && (!!data.standalone || !!data.xpubs);
}

/**
 * Carries out what {@link decideChainResult} decides for one chain's balance result.
 *
 * @remarks
 * Both balance layers land here so the ledger is written in exactly one place: the network query
 * owns its result through a backend task, the cache-only read resolves directly, and neither
 * difference reaches the bookkeeping.
 */
export function useChainSettlement(): UseChainSettlementReturn {
  const { updateBalances } = useBalancesStore();
  const { isStale, updateTimestamps } = useBlockchainRefreshTimestampsStore();
  const { invalidate, markCompleted } = useTaskOrchestrator();

  const refreshTsOf = (blockchain: string, balances: BlockchainBalances): number | undefined =>
    balances.lastRefreshTs ? byChainKey(balances.lastRefreshTs)[blockchain] : undefined;

  const writeBalances = (blockchain: string, balances: BlockchainBalances): void => {
    if (balances.lastRefreshTs)
      updateTimestamps(byChainKey(balances.lastRefreshTs));

    const perAccount = balances.perAccount[blockchain];

    if (isBtcBalances(perAccount))
      updateBalances(blockchain, convertBtcBalances(blockchain, balances.totals, perAccount));
    else
      updateBalances(blockchain, balances);
  };

  const settleFailure = (blockchain: string, error: TaskError, decision: ChainResultDecision): Result<void, TaskError> => {
    if (isActionable(error))
      logger.error(error.message);
    if (decision === ChainResultDecision.FORGET_EARLIER)
      invalidate(chainBalancesActivity.kind, ...chainBalancesActivity.partsOf({ chain: blockchain }));
    return err(error);
  };

  const settleSuccess = (blockchain: string, balances: BlockchainBalances, decision: ChainResultDecision, onApplied?: () => void): Result<void, TaskError> => {
    if (decision === ChainResultDecision.APPLY) {
      writeBalances(blockchain, balances);
      onApplied?.();
    }
    else {
      logger.debug(`refused a balance result for ${blockchain}: the chain already holds newer balances`);
    }
    markCompleted(chainBalancesActivity.kind, ...chainBalancesActivity.partsOf({ chain: blockchain }));
    return ok(undefined);
  };

  /** @returns `ok` for an overtaken result, so a failure cannot trigger a hydration retry. */
  const settleChain = (
    blockchain: string,
    result: Result<BlockchainBalances, TaskError>,
    { isTargeted = false, onApplied, overtaken = false }: ChainSettlementOptions = {},
  ): Result<void, TaskError> => {
    const decision = decideChainResult({
      failed: isErr(result),
      isTargeted,
      olderThanStored: !isErr(result) && isStale(blockchain, refreshTsOf(blockchain, result.value)),
      overtaken,
    });

    if (decision === ChainResultDecision.DROP_OVERTAKEN) {
      logger.debug(`dropped a balance result for ${blockchain}: a network result overtook it`);
      return ok(undefined);
    }

    return isErr(result)
      ? settleFailure(blockchain, result.error, decision)
      : settleSuccess(blockchain, result.value, decision, onApplied);
  };

  return { settleChain };
}
