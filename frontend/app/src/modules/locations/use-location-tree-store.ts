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

  /** The locations new data can be assigned to: every active location but the total. */
  const assignableNodes = computed<LocationNode[]>(() =>
    get(nodes).filter(node => node.isActive && node.identifier !== ROOT_LOCATION));

  const getNode = (identifier: string): LocationNode | undefined => get(nodesById).get(identifier);

  const childrenOf = (identifier: string): LocationNode[] => get(childrenById).get(identifier) ?? [];

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
    pathOf,
    setNodes,
    subtreeOf,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLocationTreeStore, import.meta.hot));
