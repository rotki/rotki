import type { ComputedRef, Ref } from 'vue';
import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';
import { type RpcProviderCandidate, toRpcNodePayload } from '@/modules/settings/general/rpc/providers/rpc-provider-plan';
import { type RpcNodesByChain, useRpcNodesByChain } from '@/modules/settings/general/rpc/providers/use-rpc-nodes-by-chain';

export const RPC_SETUP_STATUS = {
  ADDED: 'added',
  FAILED: 'failed',
  PENDING: 'pending',
  RUNNING: 'running',
  UPDATED: 'updated',
} as const;

type RpcSetupStatus = typeof RPC_SETUP_STATUS[keyof typeof RPC_SETUP_STATUS];

export interface RpcSetupRow {
  /** Whether the node reported archive support once connected, known only for a kept node. */
  archive?: boolean;
  chain: string;
  endpoint: string;
  /** Why the chain was left without the node, taken from the backend's own message. */
  error?: string;
  name: string;
  status: RpcSetupStatus;
}

export interface RpcSetupSummary {
  added: number;
  archive: number;
  failed: number;
  total: number;
}

/** Undoes whatever put the endpoint in place, so a node that cannot connect leaves no trace. */
interface RpcNodePlacement {
  identifier: number;
  revert: () => Promise<unknown>;
}

interface UseRpcProviderSetupReturn {
  /** Reads the nodes each chain already has, so the plan can tell which are already covered. */
  loadExisting: (chains: string[]) => Promise<RpcNodesByChain>;
  /** Resets the rows, so the dialog can be reopened on a different key. */
  reset: () => void;
  /** Runs a subset again, keeping the rows of the chains it is not retrying. */
  retry: (candidates: RpcProviderCandidate[]) => Promise<void>;
  /** One row per candidate, updated in place as the run walks them. */
  rows: Readonly<Ref<RpcSetupRow[]>>;
  /** Whether a run is in flight. */
  running: Readonly<Ref<boolean>>;
  /** Adds each candidate, connects it, and undoes it again when it cannot be reached. */
  run: (candidates: RpcProviderCandidate[]) => Promise<void>;
  /** Abandons the run in flight, leaving the chains behind the one it is on untouched. */
  stop: () => void;
  /** What the run ended up doing, for the dialog's footer. */
  summary: ComputedRef<RpcSetupSummary>;
}

/**
 * Applies a provider fan-out one chain at a time.
 *
 * @remarks
 * Each chain is placed, then connected, and one that cannot be reached is undone again: the backend
 * only reports archive support and the chain id a node actually answers on once connected, so a
 * node that is never connected is both unverified and invisible. Chains are walked sequentially
 * because every connect does real network work against the provider.
 */
export function useRpcProviderSetup(): UseRpcProviderSetupReturn {
  const { readNodes: loadExisting } = useRpcNodesByChain();
  const rows = ref<RpcSetupRow[]>([]);
  const running = shallowRef<boolean>(false);

  /**
   * Identifies the run allowed to write.
   *
   * @remarks
   * Closing the dialog abandons a run that is still awaiting the network, so both `stop` and the
   * next `run` bump this and every write from the older loop is dropped on the way in.
   */
  let currentRun = 0;

  const summary = computed<RpcSetupSummary>(() => {
    const list = get(rows);
    const kept = list.filter(row => row.status === RPC_SETUP_STATUS.ADDED || row.status === RPC_SETUP_STATUS.UPDATED);
    return {
      added: kept.length,
      archive: list.filter(row => row.archive).length,
      failed: list.filter(row => row.status === RPC_SETUP_STATUS.FAILED).length,
      total: list.length,
    };
  });

  function update(token: number, chain: string, patch: Partial<RpcSetupRow>): void {
    if (token !== currentRun)
      return;

    set(rows, get(rows).map(row => row.chain === chain ? { ...row, ...patch } : row));
  }

  function pendingRow(candidate: RpcProviderCandidate): RpcSetupRow {
    return {
      chain: candidate.chain,
      endpoint: candidate.endpoint,
      name: candidate.name,
      status: RPC_SETUP_STATUS.PENDING,
    };
  }

  /**
   * Undoes a placement.
   *
   * @remarks
   * A failed revert is swallowed on purpose: the row already carries the reason the chain has no
   * working node, and a second error about the cleanup would bury it.
   */
  async function rollback(placement: RpcNodePlacement): Promise<void> {
    await placement.revert().catch(() => undefined);
  }

  /**
   * Puts the candidate's endpoint on its chain, as an update of the key it replaces or as a new
   * node, and hands back the way to undo that.
   *
   * @remarks
   * An add that fails because the endpoint is already there is not an error: an earlier attempt can
   * leave a node behind that was never connected, and adopting it is what lets a retry get past it.
   */
  async function place(
    api: ReturnType<typeof useEvmNodesApi>,
    candidate: RpcProviderCandidate,
  ): Promise<RpcNodePlacement | undefined> {
    const find = async (): Promise<BlockchainRpcNode | undefined> =>
      (await api.fetchEvmNodes()).find(node => node.endpoint === candidate.endpoint);

    const previous = candidate.outdated;
    if (previous) {
      await api.editEvmNode({ ...previous, endpoint: candidate.endpoint });
      return { identifier: previous.identifier, revert: async () => api.editEvmNode(previous) };
    }

    try {
      await api.addEvmNode(toRpcNodePayload(candidate));
    }
    catch (error: unknown) {
      if (!await find())
        throw error;
    }

    const added = await find();
    return added ? { identifier: added.identifier, revert: async () => api.deleteEvmNode(added.identifier) } : undefined;
  }

  async function apply(token: number, candidate: RpcProviderCandidate): Promise<void> {
    const api = useEvmNodesApi(candidate.chain);
    update(token, candidate.chain, { status: RPC_SETUP_STATUS.RUNNING });

    let placement: RpcNodePlacement | undefined;
    try {
      placement = await place(api, candidate);
    }
    catch (error: unknown) {
      update(token, candidate.chain, { error: getErrorMessage(error), status: RPC_SETUP_STATUS.FAILED });
      return;
    }

    if (!placement) {
      update(token, candidate.chain, { status: RPC_SETUP_STATUS.FAILED });
      return;
    }

    const kept = candidate.outdated ? RPC_SETUP_STATUS.UPDATED : RPC_SETUP_STATUS.ADDED;
    try {
      const { errors } = await api.reConnectNode(placement.identifier);
      if (errors.length > 0) {
        await rollback(placement);
        update(token, candidate.chain, { error: errors[0].error, status: RPC_SETUP_STATUS.FAILED });
        return;
      }

      const connected = (await api.fetchEvmNodes()).find(node => node.identifier === placement.identifier);
      update(token, candidate.chain, { archive: connected?.isArchive === true, status: kept });
    }
    catch (error: unknown) {
      await rollback(placement);
      update(token, candidate.chain, { error: getErrorMessage(error), status: RPC_SETUP_STATUS.FAILED });
    }
  }

  async function walk(candidates: RpcProviderCandidate[]): Promise<void> {
    const token = ++currentRun;
    set(running, true);
    try {
      for (const candidate of candidates) {
        if (token !== currentRun)
          return;

        await apply(token, candidate);
      }
    }
    finally {
      if (token === currentRun)
        set(running, false);
    }
  }

  async function run(candidates: RpcProviderCandidate[]): Promise<void> {
    set(rows, candidates.map(pendingRow));
    await walk(candidates);
  }

  async function retry(candidates: RpcProviderCandidate[]): Promise<void> {
    const retried = new Map(candidates.map(candidate => [candidate.chain, candidate]));
    set(rows, get(rows).map((row) => {
      const candidate = retried.get(row.chain);
      return candidate ? pendingRow(candidate) : row;
    }));
    await walk(candidates);
  }

  function stop(): void {
    currentRun += 1;
    set(running, false);
  }

  function reset(): void {
    set(rows, []);
  }

  return {
    loadExisting,
    reset,
    retry,
    rows: shallowReadonly(rows),
    running: readonly(running),
    run,
    stop,
    summary,
  };
}
