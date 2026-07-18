import type { MatchSuggestions } from '@/modules/history/events/matching/types';
import { snakeCaseTransformer } from '@/modules/core/api';
import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';

interface UseBridgeMatchingApiReturn {
  getUnmatchedBridgeTransactions: (onlyIgnored?: boolean) => Promise<string[]>;
  getBridgeMatches: (bridgeEvent: string, timeRange: number, onlyExpectedAssets: boolean, tolerance: string) => Promise<MatchSuggestions>;
  matchBridgeTransactions: (bridgeEvent: number, matchedEvents?: number[], external?: boolean) => Promise<boolean>;
  unlinkBridgeTransaction: (identifier: number) => Promise<boolean>;
  triggerBridgeMatching: () => Promise<PendingTask>;
}

export function useBridgeMatchingApi(): UseBridgeMatchingApiReturn {
  const { triggerTask } = useTaskApi();

  const getUnmatchedBridgeTransactions = async (onlyIgnored?: boolean): Promise<string[]> =>
    api.get<string[]>('/history/events/match/bridges', {
      params: onlyIgnored !== undefined ? snakeCaseTransformer({ onlyIgnored }) : undefined,
    });

  const getBridgeMatches = async (bridgeEvent: string, timeRange: number, onlyExpectedAssets: boolean, tolerance: string): Promise<MatchSuggestions> =>
    api.post<MatchSuggestions>('/history/events/match/bridges', {
      bridgeEvent,
      onlyExpectedAssets,
      timeRange,
      tolerance,
    });

  const matchBridgeTransactions = async (bridgeEvent: number, matchedEvents?: number[], external = false): Promise<boolean> =>
    api.put<boolean>('/history/events/match/bridges', {
      bridgeEvent,
      external,
      ...(matchedEvents && matchedEvents.length > 0 && { matchedEvents }),
    });

  const unlinkBridgeTransaction = async (identifier: number): Promise<boolean> =>
    api.delete<boolean>('/history/events/match/bridges', {
      body: { identifier },
    });

  const triggerBridgeMatching = async (): Promise<PendingTask> => {
    const response = await triggerTask('bridge_matching');
    return PendingTaskSchema.parse(response);
  };

  return {
    getBridgeMatches,
    getUnmatchedBridgeTransactions,
    matchBridgeTransactions,
    triggerBridgeMatching,
    unlinkBridgeTransaction,
  };
}
