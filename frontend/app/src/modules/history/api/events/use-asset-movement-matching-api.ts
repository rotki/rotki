import { snakeCaseTransformer } from '@/modules/core/api';
import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';

interface AssetMovementMatchSuggestions {
  closeMatches: number[];
  otherEvents: number[];
}

interface UseAssetMovementMatchingApiReturn {
  getUnmatchedAssetMovements: (onlyIgnored?: boolean) => Promise<string[]>;
  getAssetMovementMatches: (assetMovement: string, timeRange: number, onlyExpectedAssets: boolean, tolerance: string) => Promise<AssetMovementMatchSuggestions>;
  matchAssetMovements: (assetMovement: number, matchedEvents?: number[], external?: boolean) => Promise<boolean>;
  unlinkAssetMovement: (identifier: number) => Promise<boolean>;
  triggerAssetMovementMatching: () => Promise<PendingTask>;
}

export function useAssetMovementMatchingApi(): UseAssetMovementMatchingApiReturn {
  const { triggerTask } = useTaskApi();

  const getUnmatchedAssetMovements = async (onlyIgnored?: boolean): Promise<string[]> =>
    api.get<string[]>('/history/events/match/asset_movements', {
      params: onlyIgnored !== undefined ? snakeCaseTransformer({ onlyIgnored }) : undefined,
    });

  const getAssetMovementMatches = async (assetMovement: string, timeRange: number, onlyExpectedAssets: boolean, tolerance: string): Promise<AssetMovementMatchSuggestions> =>
    api.post<AssetMovementMatchSuggestions>('/history/events/match/asset_movements', {
      assetMovement,
      onlyExpectedAssets,
      timeRange,
      tolerance,
    });

  /**
   * Resolves an asset movement, either by linking it to events or by declaring it unmatchable.
   *
   * @remarks
   * Without matched events the movement is marked as having no match, unless `external` is set,
   * which resolves it as moving to or from an untracked address instead: a withdrawal becomes a
   * payment and a deposit becomes income.
   *
   * @param assetMovement - identifier of the movement's own event
   * @param matchedEvents - identifiers of the events to link; an empty or absent list resolves the
   * movement without a counterpart
   * @param external - resolve the movement as external rather than as having no match
   * @returns whether the backend accepted the resolution
   */
  const matchAssetMovements = async (assetMovement: number, matchedEvents?: number[], external = false): Promise<boolean> =>
    api.put<boolean>('/history/events/match/asset_movements', {
      assetMovement,
      ...(external && { external }),
      ...(matchedEvents && matchedEvents.length > 0 && { matchedEvents }),
    });

  const unlinkAssetMovement = async (identifier: number): Promise<boolean> =>
    api.delete<boolean>('/history/events/match/asset_movements', {
      body: { identifier },
    });

  const triggerAssetMovementMatching = async (): Promise<PendingTask> => {
    const response = await triggerTask('asset_movement_matching');
    return PendingTaskSchema.parse(response);
  };

  return {
    getAssetMovementMatches,
    getUnmatchedAssetMovements,
    matchAssetMovements,
    triggerAssetMovementMatching,
    unlinkAssetMovement,
  };
}
