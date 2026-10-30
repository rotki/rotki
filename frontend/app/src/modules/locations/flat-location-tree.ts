import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { ROOT_LOCATION } from '@/modules/locations/use-location-tree-store';

/**
 * The location tree as a flat list below the total, built from the location details the backend
 * serves at `/locations/all`.
 *
 * @remarks
 * It stands in for the tree until the backend serves one at `GET /locations`. With every location
 * directly below the total, none of them is a category, every path is a single name and no two
 * names are shared, so views reading the tree behave as they did with the plain location list.
 */
export function flatLocationTree(locations: Readonly<Record<string, { readonly label?: string }>>): LocationNode[] {
  const child = (identifier: string): LocationNode => ({
    icon: null,
    identifier,
    image: null,
    isActive: true,
    isBuiltin: true,
    name: locations[identifier]?.label ?? identifier,
    parentIdentifier: ROOT_LOCATION,
  });
  return [
    { icon: null, identifier: ROOT_LOCATION, image: null, isActive: true, isBuiltin: true, name: 'Total', parentIdentifier: null },
    ...Object.keys(locations).filter(identifier => identifier !== ROOT_LOCATION).map(child),
  ];
}
