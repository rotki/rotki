import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
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
}

/**
 * Changes to custom locations. Every change that succeeds reloads the location tree, so that
 * every view shows the new state; a failure hands back the backend's message.
 */
export function useLocationManagement(): UseLocationManagementReturn {
  const api = useLocationTreeApi();
  const { refreshLocationTree } = useLocationTree();

  async function changing<T>(change: () => Promise<T>): ResultAsync<T, string> {
    return fromAsync(async () => {
      const result = await change();
      await refreshLocationTree();
      return result;
    }, cause => getErrorMessage(cause));
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
    createLocation,
    deleteLocation,
    editLocation,
    fetchUsage,
    previewEdit,
    removeImage,
    uploadImage,
  };
}
