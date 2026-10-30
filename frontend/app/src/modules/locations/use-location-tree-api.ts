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
