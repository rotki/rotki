import type { LocationNode } from '@/modules/locations/use-location-tree-api';

/** A location tree node, built-in and active unless the overrides say otherwise. */
export function createLocationNode(identifier: string, parentIdentifier: string | null, name: string, overrides: Partial<LocationNode> = {}): LocationNode {
  return { icon: null, identifier, image: null, isActive: true, isBuiltin: true, name, parentIdentifier, ...overrides };
}
