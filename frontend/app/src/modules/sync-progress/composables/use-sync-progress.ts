import type { ComputedRef } from 'vue';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/messaging/types';
import { useHistoryStore } from '@/store/history';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import {
  type ChainProgress,
  type DecodingProgress,
  type LocationProgress,
  LocationStatus,
  type ProtocolCacheProgress,
  SyncPhase,
  type SyncProgressState,
} from '../types';
import { useChainProgress } from './use-chain-progress';

interface UseSyncProgressReturn {
  state: ComputedRef<SyncProgressState>;
  chains: ComputedRef<ChainProgress[]>;
  locations: ComputedRef<LocationProgress[]>;
  decoding: ComputedRef<DecodingProgress[]>;
  protocolCache: ComputedRef<ProtocolCacheProgress[]>;
  phase: ComputedRef<SyncPhase>;
  overallProgress: ComputedRef<number>;
  isActive: ComputedRef<boolean>;
  canDismiss: ComputedRef<boolean>;
  totalChains: ComputedRef<number>;
  completedChains: ComputedRef<number>;
  totalLocations: ComputedRef<number>;
  completedLocations: ComputedRef<number>;
  totalAccounts: ComputedRef<number>;
  uniqueAddresses: ComputedRef<number>;
  completedAccounts: ComputedRef<number>;
}

function mapLocationStatus(data: HistoryEventsQueryData): LocationProgress {
  let status: LocationProgress['status'];

  switch (data.status) {
    case HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED:
      status = LocationStatus.COMPLETE;
      break;
    case HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED:
      status = LocationStatus.PENDING;
      break;
    case HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE:
      status = LocationStatus.QUERYING;
      break;
  }

  return {
    eventType: data.eventType || undefined,
    location: data.location,
    name: data.name,
    status,
  };
}

/**
 * Weights for calculating overall sync progress.
 * Transactions have the highest weight (50%) as they're the most time-consuming operation.
 * Events (exchange history) have medium weight (30%) as they involve external API calls.
 * Decoding has the lowest weight (20%) as it's a local operation that's typically fast.
 */
const PROGRESS_WEIGHTS = {
  decoding: 0.2,
  events: 0.3,
  transactions: 0.5,
} as const;

export function useSyncProgress(): UseSyncProgressReturn {
  const txStore = useTxQueryStatusStore();
  const eventsStore = useEventsQueryStatusStore();
  const historyStore = useHistoryStore();

  const { queryStatus: txQueryStatus } = toRefs(txStore);
  const { queryStatus: eventsQueryStatus } = toRefs(eventsStore);
  // Use decodingSyncStatus for sync progress - it's not reset by fetchUndecodedTransactionsBreakdown
  const { decodingSyncStatus: rawDecodingStatus, protocolCacheStatus: rawProtocolCacheStatus } = toRefs(historyStore);

  const chains = useChainProgress(txQueryStatus);

  const locations = computed<LocationProgress[]>(() => {
    const statusMap = get(eventsQueryStatus);
    return Object.values(statusMap)
      .map(mapLocationStatus)
      .sort((a, b) => {
        // Sort by: querying first, then pending, then complete
        const priority: Record<LocationProgress['status'], number> = {
          [LocationStatus.QUERYING]: 0,
          [LocationStatus.PENDING]: 1,
          [LocationStatus.COMPLETE]: 2,
        };
        return priority[a.status] - priority[b.status];
      });
  });

  const decoding = computed<DecodingProgress[]>(() =>
    get(rawDecodingStatus).map(item => ({
      chain: item.chain,
      processed: item.processed,
      progress: item.total > 0 ? Math.round((item.processed / item.total) * 100) : 0,
      total: item.total,
    })),
  );

  const protocolCache = computed<ProtocolCacheProgress[]>(() =>
    get(rawProtocolCacheStatus).map(item => ({
      chain: item.chain,
      processed: item.processed,
      progress: item.total > 0 ? Math.round((item.processed / item.total) * 100) : 0,
      protocol: item.protocol,
      total: item.total,
    })),
  );

  const totalChains = computed<number>(() => get(chains).length);
  const completedChains = computed<number>(() =>
    get(chains).filter(c => c.completed === c.total && c.total > 0).length,
  );

  const totalLocations = computed<number>(() => get(locations).length);
  const completedLocations = computed<number>(() =>
    get(locations).filter(l => l.status === LocationStatus.COMPLETE).length,
  );

  const totalAccounts = computed<number>(() =>
    get(chains).reduce((sum, c) => sum + c.total, 0),
  );

  const uniqueAddresses = computed<number>(() => {
    const allAddresses = get(chains).flatMap(c => c.addresses.map(a => a.address.toLowerCase()));
    return new Set(allAddresses).size;
  });

  const completedAccounts = computed<number>(() =>
    get(chains).reduce((sum, c) => sum + c.completed, 0),
  );

  const hasTxActivity = computed<boolean>(() => get(totalAccounts) > 0);
  const hasEventsActivity = computed<boolean>(() => get(totalLocations) > 0);
  const hasDecodingActivity = computed<boolean>(() => get(decoding).length > 0);

  const overallProgress = computed<number>(() => {
    const hasTx = get(hasTxActivity);
    const hasEvents = get(hasEventsActivity);
    const hasDecoding = get(hasDecodingActivity);

    if (!hasTx && !hasEvents && !hasDecoding)
      return 0;

    let totalWeight = 0;
    let weightedProgress = 0;

    if (hasTx) {
      const txProgress = get(totalAccounts) > 0
        ? get(completedAccounts) / get(totalAccounts)
        : 0;
      weightedProgress += txProgress * PROGRESS_WEIGHTS.transactions;
      totalWeight += PROGRESS_WEIGHTS.transactions;
    }

    if (hasEvents) {
      const eventsProgress = get(totalLocations) > 0
        ? get(completedLocations) / get(totalLocations)
        : 0;
      weightedProgress += eventsProgress * PROGRESS_WEIGHTS.events;
      totalWeight += PROGRESS_WEIGHTS.events;
    }

    if (hasDecoding) {
      const decodingItems = get(decoding);
      const avgDecodingProgress = decodingItems.length > 0
        ? decodingItems.reduce((sum, d) => sum + d.progress, 0) / decodingItems.length / 100
        : 0;
      weightedProgress += avgDecodingProgress * PROGRESS_WEIGHTS.decoding;
      totalWeight += PROGRESS_WEIGHTS.decoding;
    }

    return totalWeight > 0 ? Math.round((weightedProgress / totalWeight) * 100) : 0;
  });

  const isActive = computed<boolean>(() =>
    get(hasTxActivity) || get(hasEventsActivity) || get(hasDecodingActivity),
  );

  const phase = computed<SyncPhase>(() => {
    if (!get(isActive))
      return SyncPhase.IDLE;

    // Use count-based completion checks (same as header display)
    const chainsTotal = get(totalChains);
    const chainsCompleted = get(completedChains);
    const locationsTotal = get(totalLocations);
    const locationsCompleted = get(completedLocations);
    const decodingItems = get(decoding);

    const allChainsDone = chainsTotal === 0 || chainsCompleted === chainsTotal;
    const allLocationsDone = locationsTotal === 0 || locationsCompleted === locationsTotal;
    const allDecodingDone = decodingItems.every(d => d.processed >= d.total);

    if (allChainsDone && allLocationsDone && allDecodingDone)
      return SyncPhase.COMPLETE;

    return SyncPhase.SYNCING;
  });

  const canDismiss = computed<boolean>(() => get(phase) === SyncPhase.COMPLETE);

  const state = computed<SyncProgressState>(() => ({
    canDismiss: get(canDismiss),
    chains: get(chains),
    completedAccounts: get(completedAccounts),
    completedChains: get(completedChains),
    completedLocations: get(completedLocations),
    decoding: get(decoding),
    isActive: get(isActive),
    locations: get(locations),
    overallProgress: get(overallProgress),
    phase: get(phase),
    protocolCache: get(protocolCache),
    totalAccounts: get(totalAccounts),
    totalChains: get(totalChains),
    totalLocations: get(totalLocations),
  }));

  return {
    canDismiss,
    chains,
    completedAccounts,
    completedChains,
    completedLocations,
    decoding,
    isActive,
    locations,
    overallProgress,
    phase,
    protocolCache,
    state,
    totalAccounts,
    totalChains,
    totalLocations,
    uniqueAddresses,
  };
}
