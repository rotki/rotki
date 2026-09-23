import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

interface UseLocationTreeExpansionReturn {
  isExpanded: (identifier: string) => boolean;
  toggle: (identifier: string) => void;
  /** Opens every location above the given one, so its row shows. */
  reveal: (identifier: string) => void;
}

/**
 * Which locations of the location manager show the locations below them.
 *
 * @remarks
 * On arrival, a location is open when a custom location sits somewhere below it, so the user's
 * own locations show while the built-in catalog stays folded. That starting point is taken once,
 * when the tree first loads: later changes do not fold or unfold anything behind the user's back,
 * and a location the user just changed is brought into view with {@link reveal} instead.
 */
export function useLocationTreeExpansion(): UseLocationTreeExpansionReturn {
  const toggled = ref<Map<string, boolean>>(new Map());
  const openOnArrival = shallowRef<ReadonlySet<string>>();

  const treeStore = useLocationTreeStore();
  const { nodes } = storeToRefs(treeStore);

  const ancestorsOf = (identifier: string): string[] =>
    treeStore.pathOf(identifier).slice(0, -1).map(ancestor => ancestor.identifier);

  const isExpanded = (identifier: string): boolean =>
    get(toggled).get(identifier) ?? get(openOnArrival)?.has(identifier) ?? false;

  const toggle = (identifier: string): void => {
    set(toggled, new Map(get(toggled)).set(identifier, !isExpanded(identifier)));
  };

  const reveal = (identifier: string): void => {
    const next = new Map(get(toggled));
    for (const ancestor of ancestorsOf(identifier))
      next.set(ancestor, true);
    set(toggled, next);
  };

  watch(nodes, (value) => {
    if (get(openOnArrival) === undefined && value.length > 0)
      set(openOnArrival, new Set(value.filter(node => !node.isBuiltin).flatMap(node => ancestorsOf(node.identifier))));
  }, { immediate: true });

  return { isExpanded, reveal, toggle };
}
