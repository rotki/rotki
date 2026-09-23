import type { LocationNode } from '@/modules/locations/use-location-tree-api';

export const ROOT_LOCATION = 'total';

/** The location tree the backend serves at `GET /locations`, with the lookups views need. */
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

  /** The locations new data can be assigned to: every active location that is not a category. */
  const assignableNodes = computed<LocationNode[]>(() =>
    get(nodes).filter(node => node.isActive && !isCategory(node)));

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
    return path.length > 0 ? path.map(node => node.name).join(' › ') : identifier;
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
   * The name to show for a location where only a name fits: its own name, or its path when another
   * location shares that name, so `Banks › ING` and `Exchanges › ING` stay apart. An unknown
   * location gives undefined.
   */
  const distinctNameOf = (identifier: string): string | undefined => {
    const node = getNode(identifier);
    if (!node)
      return undefined;
    return (get(nameCounts).get(node.name.toLowerCase()) ?? 0) > 1 ? pathLabelOf(identifier) : node.name;
  };

  /** Orders locations the way the tree lists them: each one after its ancestors, siblings by name. */
  const sortByTree = (identifiers: readonly string[]): string[] => {
    const key = (identifier: string): string => pathOf(identifier).map(node => node.name.toLowerCase()).join('\u0000');
    return [...identifiers].sort((a, b) => key(a).localeCompare(key(b)));
  };

  /** The location and every location below it. */
  const subtreeOf = (identifier: string): Set<string> => {
    const subtree = new Set<string>();
    const pending = [identifier];
    while (pending.length > 0) {
      const current = pending.pop();
      if (current === undefined || subtree.has(current))
        continue;
      subtree.add(current);
      pending.push(...childrenOf(current).map(child => child.identifier));
    }
    return subtree;
  };

  const setNodes = (value: LocationNode[]): void => {
    set(nodes, value);
  };

  return {
    assignableNodes,
    childrenOf,
    getNode,
    nodes,
    distinctNameOf,
    pathLabelOf,
    pathOf,
    setNodes,
    sortByTree,
    subtreeOf,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLocationTreeStore, import.meta.hot));
