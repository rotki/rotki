import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import { toRequestError } from '@/modules/core/api/request-result';
import {
  type LocationCreatePayload,
  type LocationEditPayload,
  type LocationEditResult,
  type LocationNode,
  type LocationUsage,
  useLocationTreeApi,
} from '@/modules/locations/use-location-tree-api';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

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

/** Runs a request, handing back the backend's message when it fails. */
async function request<T>(call: () => Promise<T>): ResultAsync<T, string> {
  return fromAsync(call, cause => toRequestError(cause).message);
}

/**
 * Changes to custom locations. Every change that succeeds is applied to the location tree store
 * from the backend's answer, so every view shows the new state without reloading the tree; a
 * failure hands back the backend's message.
 *
 * @remarks
 * Each change touches one location: a move only changes its parent, and the paths below it follow
 * from the tree.
 */
export function useLocationManagement(): UseLocationManagementReturn {
  const api = useLocationTreeApi();
  const treeStore = useLocationTreeStore();

  const withImage = (identifier: string, image: string | null): void => {
    const node = treeStore.getNode(identifier);
    if (node)
      treeStore.upsertNode({ ...node, image });
  };

  const createLocation = async (payload: LocationCreatePayload): ResultAsync<LocationNode, string> =>
    request(async () => {
      const created = await api.addLocation(payload);
      treeStore.upsertNode(created);
      return created;
    });

  const editLocation = async (identifier: string, payload: LocationEditPayload): ResultAsync<LocationEditResult, string> =>
    request(async () => {
      const result = await api.editLocation(identifier, { ...payload, dryRun: false });
      treeStore.upsertNode(result.location);
      return result;
    });

  const previewEdit = async (identifier: string, payload: LocationEditPayload): ResultAsync<LocationEditResult, string> =>
    request(async () => api.editLocation(identifier, { ...payload, dryRun: true }));

  const fetchUsage = async (identifier: string): ResultAsync<LocationUsage, string> =>
    request(async () => api.fetchLocationUsage(identifier));

  const deleteLocation = async (identifier: string): ResultAsync<boolean, string> =>
    request(async () => {
      const deleted = await api.deleteLocation(identifier);
      treeStore.removeNode(identifier);
      return deleted;
    });

  const uploadImage = async (identifier: string, file: File): ResultAsync<string, string> =>
    request(async () => {
      const image = await api.uploadLocationImage(identifier, file);
      withImage(identifier, image);
      return image;
    });

  const removeImage = async (identifier: string): ResultAsync<boolean, string> =>
    request(async () => {
      const removed = await api.deleteLocationImage(identifier);
      withImage(identifier, null);
      return removed;
    });

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
