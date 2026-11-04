import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useLocationTree } from '@/modules/locations/use-location-tree';
import {
  type LocationCreatePayload,
  type LocationEditPayload,
  type LocationEditResult,
  type LocationNode,
  type LocationUsage,
  useLocationTreeApi,
} from '@/modules/locations/use-location-tree-api';

interface UseLocationManagementReturn {
  createLocation: (payload: LocationCreatePayload) => ResultAsync<LocationNode, string>;
  editLocation: (identifier: string, payload: LocationEditPayload) => ResultAsync<LocationEditResult, string>;
  /** Checks an edit without saving it, for the paths a move changes. */
  previewEdit: (identifier: string, payload: LocationEditPayload) => ResultAsync<LocationEditResult, string>;
  fetchUsage: (identifier: string) => ResultAsync<LocationUsage, string>;
  deleteLocation: (identifier: string) => ResultAsync<boolean, string>;
  uploadImage: (identifier: string, file: File) => ResultAsync<string, string>;
  removeImage: (identifier: string) => ResultAsync<boolean, string>;
  /** Runs several changes, such as a save and its image, and reloads the tree once after them. */
  batch: <T>(changes: () => Promise<T>) => Promise<T>;
}

/**
 * Changes to custom locations. Every change that succeeds reloads the location tree, so that
 * every view shows the new state; a failure hands back the backend's message.
 */
export function useLocationManagement(): UseLocationManagementReturn {
  const api = useLocationTreeApi();
  const { refreshLocationTree } = useLocationTree();

  /** How many batches are running; changes inside one leave the reload to the last to end. */
  let openBatches = 0;
  let changedInBatch = false;

  async function changing<T>(change: () => Promise<T>): ResultAsync<T, string> {
    return fromAsync(async () => {
      const result = await change();
      if (openBatches > 0)
        changedInBatch = true;
      else
        await refreshLocationTree();
      return result;
    }, cause => getErrorMessage(cause));
  }

  /**
   * Runs the changes and reloads the tree once after them, if any of them was saved.
   *
   * @remarks
   * Batches that overlap or nest share one reload, run when the last of them ends. The changes
   * are already saved when it runs, so a failed reload is only logged: the tree catches up with
   * the next reload.
   */
  async function batch<T>(changes: () => Promise<T>): Promise<T> {
    openBatches += 1;
    try {
      return await changes();
    }
    finally {
      openBatches -= 1;
      if (openBatches === 0 && changedInBatch) {
        changedInBatch = false;
        await refreshLocationTree().catch((error: unknown) => {
          logger.error('Could not reload the location tree', error);
        });
      }
    }
  }

  const createLocation = async (payload: LocationCreatePayload): ResultAsync<LocationNode, string> =>
    changing(async () => api.addLocation(payload));

  const editLocation = async (identifier: string, payload: LocationEditPayload): ResultAsync<LocationEditResult, string> =>
    changing(async () => api.editLocation(identifier, { ...payload, dryRun: false }));

  const previewEdit = async (identifier: string, payload: LocationEditPayload): ResultAsync<LocationEditResult, string> =>
    fromAsync(async () => api.editLocation(identifier, { ...payload, dryRun: true }), cause => getErrorMessage(cause));

  const fetchUsage = async (identifier: string): ResultAsync<LocationUsage, string> =>
    fromAsync(async () => api.fetchLocationUsage(identifier), cause => getErrorMessage(cause));

  const deleteLocation = async (identifier: string): ResultAsync<boolean, string> =>
    changing(async () => api.deleteLocation(identifier));

  const uploadImage = async (identifier: string, file: File): ResultAsync<string, string> =>
    changing(async () => api.uploadLocationImage(identifier, file));

  const removeImage = async (identifier: string): ResultAsync<boolean, string> =>
    changing(async () => api.deleteLocationImage(identifier));

  return {
    batch,
    createLocation,
    deleteLocation,
    editLocation,
    fetchUsage,
    previewEdit,
    removeImage,
    uploadImage,
  };
}
