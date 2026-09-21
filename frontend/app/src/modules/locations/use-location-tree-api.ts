import { z } from 'zod';
import { api } from '@/modules/core/api/rotki-api';

/** One node of the location tree. The root, `total`, is the only node without a parent. */
export const LocationNode = z.object({
  identifier: z.string(),
  name: z.string(),
  parentIdentifier: z.string().nullable(),
  isBuiltin: z.boolean(),
  isActive: z.boolean(),
  icon: z.string().nullable(),
  image: z.string().nullable(),
});

export type LocationNode = z.infer<typeof LocationNode>;

const LocationNodes = z.array(LocationNode);

/** The result of an edit, with the display paths from the root before and after it. */
const LocationEditResult = z.object({
  location: LocationNode,
  oldPath: z.array(z.string()),
  newPath: z.array(z.string()),
});

export type LocationEditResult = z.infer<typeof LocationEditResult>;

/** What keeps a location from being deleted: rows per table and its number of children. */
const LocationUsage = z.object({
  usage: z.record(z.string(), z.number()),
  deletable: z.boolean(),
});

export type LocationUsage = z.infer<typeof LocationUsage>;

const LocationAliases = z.array(z.object({
  alias: z.string(),
  locationIdentifier: z.string(),
}));

export type LocationAliases = z.infer<typeof LocationAliases>;

export interface LocationCreatePayload {
  readonly name: string;
  readonly parentIdentifier: string;
  readonly icon?: string;
}

/**
 * The fields of a custom location to change; absent fields stay. An `icon` of null removes the
 * icon.
 */
export interface LocationEditPayload {
  readonly name?: string;
  readonly parentIdentifier?: string;
  readonly icon?: string | null;
  readonly isActive?: boolean;
  readonly dryRun?: boolean;
}

interface UseLocationTreeApiReturn {
  fetchLocationTree: () => Promise<LocationNode[]>;
  addLocation: (payload: LocationCreatePayload) => Promise<LocationNode>;
  editLocation: (identifier: string, payload: LocationEditPayload) => Promise<LocationEditResult>;
  deleteLocation: (identifier: string) => Promise<boolean>;
  fetchLocationUsage: (identifier: string) => Promise<LocationUsage>;
  uploadLocationImage: (identifier: string, file: File) => Promise<string>;
  deleteLocationImage: (identifier: string) => Promise<boolean>;
  fetchLocationAliases: () => Promise<LocationAliases>;
  setLocationAlias: (alias: string, locationIdentifier: string) => Promise<boolean>;
  deleteLocationAlias: (alias: string) => Promise<boolean>;
}

function locationPath(identifier: string, suffix = ''): string {
  return `/locations/${encodeURIComponent(identifier)}${suffix}`;
}

/**
 * The absolute url of the uploaded image of a custom location, for use as an `<img src>`.
 *
 * @remarks
 * The stored image name changes with the content, so passing it busts the browser cache after a
 * replacement.
 */
export function locationImageUrl(identifier: string, image: string): string {
  return api.buildUrl(`locations/${encodeURIComponent(identifier)}/image`, { v: image });
}

export function useLocationTreeApi(): UseLocationTreeApiReturn {
  const fetchLocationTree = async (): Promise<LocationNode[]> =>
    LocationNodes.parse(await api.get<LocationNode[]>('/locations'));

  const addLocation = async (payload: LocationCreatePayload): Promise<LocationNode> =>
    LocationNode.parse(await api.post<LocationNode>('/locations', payload));

  const editLocation = async (identifier: string, payload: LocationEditPayload): Promise<LocationEditResult> =>
    LocationEditResult.parse(await api.patch<LocationEditResult>(locationPath(identifier), payload));

  const deleteLocation = async (identifier: string): Promise<boolean> =>
    api.delete<boolean>(locationPath(identifier));

  const fetchLocationUsage = async (identifier: string): Promise<LocationUsage> =>
    LocationUsage.parse(await api.get<LocationUsage>(locationPath(identifier, '/usage')));

  const uploadLocationImage = async (identifier: string, file: File): Promise<string> => {
    const data = new FormData();
    data.append('file', file);
    const { image } = z.object({ image: z.string() }).parse(
      await api.post<unknown>(locationPath(identifier, '/image'), data),
    );
    return image;
  };

  const deleteLocationImage = async (identifier: string): Promise<boolean> =>
    api.delete<boolean>(locationPath(identifier, '/image'));

  const fetchLocationAliases = async (): Promise<LocationAliases> =>
    LocationAliases.parse(await api.get<LocationAliases>('/locations/aliases'));

  const setLocationAlias = async (alias: string, locationIdentifier: string): Promise<boolean> =>
    api.put<boolean>('/locations/aliases', { alias, locationIdentifier });

  const deleteLocationAlias = async (alias: string): Promise<boolean> =>
    api.delete<boolean>('/locations/aliases', { body: { alias } });

  return {
    addLocation,
    deleteLocation,
    deleteLocationAlias,
    deleteLocationImage,
    editLocation,
    fetchLocationAliases,
    fetchLocationTree,
    fetchLocationUsage,
    setLocationAlias,
    uploadLocationImage,
  };
}
