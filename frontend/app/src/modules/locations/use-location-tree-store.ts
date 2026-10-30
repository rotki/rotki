import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { LOCATION_PATH_SEPARATOR } from '@/modules/locations/location-path';

export const ROOT_LOCATION = 'total';

/** The location tree, with the lookups views need. */
export const useLocationTreeStore = defineStore('locations/tree', () => {
  const nodes = ref<LocationNode[]>([]);

  const nodesById = computed<Map<string, LocationNode>>(() => new Map(get(nodes).map(node => [node.identifier, node])));

  const childrenById = computed<Map<string, LocationNode[]>>(() => {
    const children = new Map<string, LocationNode[]>();
    for (const node of get(nodes)) {
      if (node.parentIdentifier !== null)
        children.set(node.parentIdentifier, [...(children.get(node.parentIdentifier) ?? []), node]);
    }
    for (const siblings of children.values())
      siblings.sort((a, b) => a.name.localeCompare(b.name));
    return children;
  });

  const getNode = (identifier: string): LocationNode | undefined => get(nodesById).get(identifier);

  const childrenOf = (identifier: string): LocationNode[] => get(childrenById).get(identifier) ?? [];

  /**
   * Whether a location only groups others, like Total, Blockchains or Banks: a built-in location
   * with built-in locations below it. A custom location stays a place of its own when the user
   * nests locations below it.
   */
  const isCategory = (node: LocationNode): boolean =>
    node.isBuiltin && childrenOf(node.identifier).some(child => child.isBuiltin);

  /**
   * The locations new data can be assigned to: every active location that is not a category.
   * Undefined while the tree has not loaded, since nothing is known to be unassignable yet.
   */
  const assignableIdentifiers = computed<ReadonlySet<string> | undefined>(() => {
    const all = get(nodes);
    if (all.length === 0)
      return undefined;
    return new Set(all.filter(node => node.isActive && !isCategory(node)).map(node => node.identifier));
  });

  /**
   * The locations from the child of the total down to the given one.
   *
   * @remarks
   * The total itself is left out: every path starts there, so it only adds noise to a breadcrumb.
   * An unknown location has an empty path.
   */
  const pathOf = (identifier: string): LocationNode[] => {
    const path: LocationNode[] = [];
    const seen = new Set<string>();
    let node = getNode(identifier);
    while (node && node.identifier !== ROOT_LOCATION && !seen.has(node.identifier)) {
      seen.add(node.identifier);
      path.unshift(node);
      node = node.parentIdentifier === null ? undefined : getNode(node.parentIdentifier);
    }
    return path;
  };

  /**
   * The path of a location as the user reads it, `Banks › ING`, which tells apart equally named
   * locations. An unknown location reads as its identifier.
   */
  const pathLabelOf = (identifier: string): string => {
    const path = pathOf(identifier);
    return path.length > 0 ? path.map(node => node.name).join(LOCATION_PATH_SEPARATOR) : identifier;
  };

  const nameCounts = computed<Map<string, number>>(() => {
    const counts = new Map<string, number>();
    for (const node of get(nodes)) {
      const key = node.name.toLowerCase();
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
  });

  /**
   * The path of a location whose name another location shares, so `Banks › ING` and
   * `Exchanges › ING` stay apart where only a name fits. Undefined for a location with a name of
   * its own or an unknown one, which then shows its display name.
   */
  const pathIfNameShared = (identifier: string): string | undefined => {
    const node = getNode(identifier);
    if (!node || (get(nameCounts).get(node.name.toLowerCase()) ?? 0) < 2)
      return undefined;
    return pathLabelOf(identifier);
  };

  const setNodes = (value: LocationNode[]): void => {
    set(nodes, value);
  };

  return {
    assignableIdentifiers,
    nodes,
    pathIfNameShared,
    pathOf,
    setNodes,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLocationTreeStore, import.meta.hot));
