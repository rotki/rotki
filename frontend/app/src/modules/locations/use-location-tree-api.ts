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

interface UseLocationTreeApiReturn {
  fetchLocationTree: () => Promise<LocationNode[]>;
}

export function useLocationTreeApi(): UseLocationTreeApiReturn {
  const fetchLocationTree = async (): Promise<LocationNode[]> =>
    LocationNodes.parse(await api.get<LocationNode[]>('/locations'));

  return { fetchLocationTree };
}
