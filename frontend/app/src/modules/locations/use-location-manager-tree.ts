import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { defaultDocument } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, nextTick, readonly, type Ref, ref, shallowRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import { type LocationRow, locationRows, onePage } from '@/modules/locations/location-rows';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { useLocationTreeExpansion } from '@/modules/locations/use-location-tree-expansion';
import { ROOT_LOCATION, useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

/** A used location the user asked to delete, with what uses it. */
interface BlockedDeletion {
  location: LocationNode;
  usage: Record<string, number>;
}

interface UseLocationManagerTreeReturn {
  /** The name the tree is searched for. */
  readonly modelSearch: Ref<string>;
  /** Whether archived locations are listed. */
  readonly modelShowArchived: Ref<boolean>;
  /** The used location whose deletion was refused, until the user dismisses it. */
  readonly modelBlockedDeletion: Ref<BlockedDeletion | undefined>;
  /** The unused location whose row asks before deleting it, until the user answers. */
  readonly modelPendingDeletion: Ref<LocationNode | undefined>;
  /** True while a confirmed deletion is in flight. */
  readonly deleting: Readonly<Ref<boolean>>;
  /** Why the last archive, restore or deletion failed, until the next one. */
  readonly actionFailure: Readonly<Ref<string | undefined>>;
  readonly rows: ComputedRef<LocationRow[]>;
  /** One page as long as the tree. */
  readonly wholeTree: ComputedRef<TablePaginationData>;
  readonly cols: ComputedRef<DataTableColumn<LocationRow>[]>;
  readonly empty: ComputedRef<{ label: string }>;
  /** The class of a row, which marks the one just brought into view. */
  readonly rowClass: (row: LocationRow) => string;
  /** Opens or folds the locations below a location. */
  readonly toggle: (identifier: string) => void;
  /** Opens the branch holding a location, marks its row and scrolls it into view. */
  readonly bringIntoView: (identifier: string) => Promise<void>;
  /** Archives or restores a location, and keeps one archived here listed. */
  readonly setArchived: (location: LocationNode, archived: boolean) => Promise<void>;
  /** Asks to delete a location: a used one shows what uses it, an unused one asks in its row. */
  readonly requestDeletion: (location: LocationNode) => Promise<void>;
  /** Deletes the location its row asked about. */
  readonly confirmDeletion: (location: LocationNode) => Promise<void>;
}

/**
 * The location manager's tree: its rows, filters, the row brought into view, and the archive and
 * deletion flows run from the rows.
 */
export function useLocationManagerTree(): UseLocationManagerTreeReturn {
  const modelSearch = shallowRef<string>('');
  const modelShowArchived = shallowRef<boolean>(false);
  /** Locations archived on this visit, which stay listed so that restoring one is a click away. */
  const archivedHere = ref<Set<string>>(new Set());
  const modelBlockedDeletion = ref<BlockedDeletion>();
  /** The unused location whose row asks before deleting it, until the user answers. */
  const modelPendingDeletion = ref<LocationNode>();
  const deleting = shallowRef<boolean>(false);
  /** Why the last archive, restore or deletion failed, until the next one. */
  const actionFailure = shallowRef<string>();

  const { t } = useI18n({ useScope: 'global' });

  const treeStore = useLocationTreeStore();
  const { deleteLocation, editLocation, fetchUsage } = useLocationManagement();
  const { isExpanded, reveal, toggle } = useLocationTreeExpansion();
  const { highlight, rowClass } = useRowHighlight<LocationRow>(row => row.node.identifier);

  const rows = computed<LocationRow[]>(() => locationRows({
    childrenOf: treeStore.childrenOf,
    isExpanded,
    keepArchived: get(archivedHere),
    root: ROOT_LOCATION,
    search: get(modelSearch),
    showArchived: get(modelShowArchived),
  }));

  /**
   * One page as long as the tree: pages would cut a subtree off from its parent, and the rows only
   * make sense in tree order.
   */
  const wholeTree = computed<TablePaginationData>(() => onePage(get(rows).length));

  const cols = computed<DataTableColumn<LocationRow>[]>(() => [{
    cellClass: 'max-w-0 w-full',
    key: 'name',
    label: t('common.name'),
  }, {
    cellClass: 'w-px',
    key: 'actions',
    label: t('common.actions_text'),
  }]);

  const empty = computed<{ label: string }>(() => {
    const term = get(modelSearch).trim();
    return { label: term === '' ? t('location_manager.empty.label') : t('location_manager.empty.search_label', { search: term }) };
  });

  /** Opens the branch holding a location, marks its row and scrolls it into view. */
  async function bringIntoView(identifier: string): Promise<void> {
    reveal(identifier);
    await nextTick();
    const row = get(rows).find(item => item.node.identifier === identifier);
    if (!row)
      return;
    highlight(row);
    defaultDocument?.querySelector(`[data-location="${CSS.escape(identifier)}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  async function setArchived(location: LocationNode, archived: boolean): Promise<void> {
    set(actionFailure, undefined);
    set(modelBlockedDeletion, undefined);
    set(modelPendingDeletion, undefined);
    const outcome = await editLocation(location.identifier, { isActive: !archived });
    if (!outcome.ok) {
      set(actionFailure, outcome.error);
      return;
    }
    if (archived)
      set(archivedHere, new Set(get(archivedHere)).add(location.identifier));
    await bringIntoView(location.identifier);
  }

  /**
   * A used location can not be deleted; the user then sees what uses it and may archive it. An unused
   * one asks in its own row before it goes.
   */
  async function requestDeletion(location: LocationNode): Promise<void> {
    set(actionFailure, undefined);
    set(modelBlockedDeletion, undefined);
    set(modelPendingDeletion, undefined);
    const usage = await fetchUsage(location.identifier);
    if (!usage.ok) {
      set(actionFailure, usage.error);
      return;
    }
    if (!usage.value.deletable) {
      set(modelBlockedDeletion, { location, usage: usage.value.usage });
      return;
    }
    set(modelPendingDeletion, location);
  }

  async function confirmDeletion(location: LocationNode): Promise<void> {
    set(deleting, true);
    const outcome = await deleteLocation(location.identifier);
    set(deleting, false);
    set(modelPendingDeletion, undefined);
    if (!outcome.ok)
      set(actionFailure, outcome.error);
  }

  return {
    actionFailure: readonly(actionFailure),
    bringIntoView,
    cols,
    confirmDeletion,
    deleting: readonly(deleting),
    empty,
    modelBlockedDeletion,
    modelPendingDeletion,
    modelSearch,
    modelShowArchived,
    requestDeletion,
    rowClass,
    rows,
    setArchived,
    toggle,
    wholeTree,
  };
}
