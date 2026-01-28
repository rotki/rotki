import { useTaskApi } from '@/composables/api/task';
import { snakeCaseTransformer } from '@/modules/api';
import { api } from '@/modules/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

export interface AssetMovementMatchSuggestions {
  closeMatches: number[];
  otherEvents: number[];
}

interface UseAssetMovementMatchingApiReturn {
  getUnmatchedAssetMovements: (onlyIgnored?: boolean) => Promise<string[]>;
  getAssetMovementMatches: (assetMovement: string, timeRange: number, onlyExpectedAssets: boolean) => Promise<AssetMovementMatchSuggestions>;
  matchAssetMovements: (assetMovement: number, matchedEvent?: number | null) => Promise<boolean>;
  unlinkAssetMovement: (assetMovement: number) => Promise<boolean>;
  triggerAssetMovementMatching: () => Promise<PendingTask>;
}

export function useAssetMovementMatchingApi(): UseAssetMovementMatchingApiReturn {
  const { triggerTask } = useTaskApi();

  const getUnmatchedAssetMovements = async (onlyIgnored?: boolean): Promise<string[]> =>
    api.get<string[]>('/history/events/match/asset_movements', {
      params: onlyIgnored !== undefined ? snakeCaseTransformer({ onlyIgnored }) : undefined,
    });

  const getAssetMovementMatches = async (assetMovement: string, timeRange: number, onlyExpectedAssets: boolean): Promise<AssetMovementMatchSuggestions> =>
    api.post<AssetMovementMatchSuggestions>('/history/events/match/asset_movements', {
      assetMovement,
      onlyExpectedAssets,
      timeRange,
    });

  const matchAssetMovements = async (assetMovement: number, matchedEvent?: number | null): Promise<boolean> =>
    api.put<boolean>('/history/events/match/asset_movements', {
      assetMovement,
      ...(matchedEvent != null && { matchedEvent }),
    });

  const unlinkAssetMovement = async (assetMovement: number): Promise<boolean> =>
    api.delete<boolean>('/history/events/match/asset_movements', {
      body: { assetMovement },
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
