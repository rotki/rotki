<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { LocationFormData } from '@/modules/locations/location-form';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';
import LocationTreeRowActions from '@/modules/locations/components/LocationTreeRowActions.vue';
import LocationTreeRowName from '@/modules/locations/components/LocationTreeRowName.vue';
import LocationUsageDialog from '@/modules/locations/components/LocationUsageDialog.vue';
import { type LocationRow, locationRows } from '@/modules/locations/location-rows';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { useLocationTreeExpansion } from '@/modules/locations/use-location-tree-expansion';
import { ROOT_LOCATION, useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const search = ref<string>('');
const showArchived = ref<boolean>(false);
/** Locations archived on this visit, which stay listed so that restoring one is a click away. */
const archivedHere = ref<Set<string>>(new Set());
const formData = ref<LocationFormData>();
const blockedDeletion = ref<{ location: LocationNode; usage: Record<string, number> }>();
/** Why the last archive, restore or deletion failed, until the next one. */
const actionFailure = shallowRef<string>();

const { t } = useI18n({ useScope: 'global' });

const treeStore = useLocationTreeStore();
const { show } = useConfirmStore();
const { deleteLocation, editLocation, fetchUsage } = useLocationManagement();
const { isExpanded, reveal, toggle } = useLocationTreeExpansion();
const { highlight, rowClass } = useRowHighlight<LocationRow>(row => row.node.identifier);

const rows = computed<LocationRow[]>(() => locationRows({
  childrenOf: treeStore.childrenOf,
  isExpanded,
  keepArchived: get(archivedHere),
  root: ROOT_LOCATION,
  search: get(search),
  showArchived: get(showArchived),
}));

/**
 * One page as long as the tree: pages would cut a subtree off from its parent, and the rows only
 * make sense in tree order.
 */
const wholeTree = computed<TablePaginationData>(() => {
  const total = get(rows).length;
  return { limit: Math.max(total, 1), page: 1, total };
});

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
  const term = get(search).trim();
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
  document.querySelector(`[data-location="${CSS.escape(identifier)}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function addBelow(parentIdentifier: string, name?: string): void {
  set(formData, { mode: 'add', name, parentIdentifier });
}

async function setArchived(location: LocationNode, archived: boolean): Promise<void> {
  set(actionFailure, undefined);
  const outcome = await editLocation(location.identifier, { isActive: !archived });
  if (!outcome.ok) {
    set(actionFailure, outcome.error);
    return;
  }
  if (archived)
    set(archivedHere, new Set(get(archivedHere)).add(location.identifier));
  await bringIntoView(location.identifier);
}

/** A used location can not be deleted; the user then sees what uses it and may archive it. */
async function requestDeletion(location: LocationNode): Promise<void> {
  set(actionFailure, undefined);
  const usage = await fetchUsage(location.identifier);
  if (!usage.ok) {
    set(actionFailure, usage.error);
    return;
  }
  if (!usage.value.deletable) {
    set(blockedDeletion, { location, usage: usage.value.usage });
    return;
  }
  show({
    message: t('location_manager.delete.message', { name: treeStore.pathLabelOf(location.identifier) }),
    primaryAction: t('common.actions.delete'),
    title: t('location_manager.delete.title'),
  }, async () => {
    const outcome = await deleteLocation(location.identifier);
    if (!outcome.ok)
      set(actionFailure, outcome.error);
  });
}

const { consumeAddQuery } = useAddQuery(() => addBelow(ROOT_LOCATION));

onMounted(async () => {
  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout :title="[t('location_manager.title')]">
    <template #buttons>
      <RuiButton
        color="primary"
        size="lg"
        data-testid="add-location"
        @click="addBelow(ROOT_LOCATION)"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('location_manager.actions.add') }}
      </RuiButton>
    </template>

    <TableFrame>
      <template #toolbar>
        <RuiTextField
          v-model="search"
          class="grow"
          color="primary"
          dense
          clearable
          prepend-icon="lu-search"
          :label="t('common.actions.search')"
          hide-details
          data-testid="location-manager-search"
        />
        <RuiSwitch
          v-model="showArchived"
          color="primary"
          hide-details
          :label="t('location_manager.show_archived')"
          data-testid="location-manager-show-archived"
        />
      </template>
      <RuiDataTable
        dense
        :rows="rows"
        :cols="cols"
        :pagination="wholeTree"
        :global-items-per-page="false"
        :item-class="rowClass"
        :empty="empty"
        hide-default-header
        hide-pagination
        row-attr="path"
        data-testid="location-manager-table"
      >
        <template
          v-if="actionFailure"
          #body.prepend
        >
          <tr>
            <td :colspan="cols.length">
              <FailureStrip
                in-table
                :title="t('location_manager.error')"
                :failure="actionFailure"
                :retryable="false"
                data-testid="location-manager-error"
              />
            </td>
          </tr>
        </template>
        <template #item.name="{ row }">
          <LocationTreeRowName
            :row="row"
            :search="search"
            @toggle="toggle(row.node.identifier)"
          />
        </template>
        <template #item.actions="{ row }">
          <LocationTreeRowActions
            :node="row.node"
            @add-child="addBelow(row.node.identifier)"
            @toggle-archive="setArchived(row.node, row.node.isActive)"
            @edit="formData = { mode: 'edit', location: row.node }"
            @delete="requestDeletion(row.node)"
          />
        </template>
        <template
          v-if="search.trim()"
          #empty-description
        >
          <p class="text-body-2 text-rui-text-secondary">
            {{ t('location_manager.empty.search_description') }}
          </p>
          <RuiButton
            color="primary"
            variant="outlined"
            class="mt-2"
            data-testid="location-manager-create-from-search"
            @click="addBelow(ROOT_LOCATION, search.trim())"
          >
            {{ t('location_manager.empty.create', { name: search.trim() }) }}
          </RuiButton>
        </template>
      </RuiDataTable>
    </TableFrame>

    <LocationFormDialog
      v-model="formData"
      @saved="bringIntoView($event)"
    />
    <LocationUsageDialog
      v-model="blockedDeletion"
      @archive="setArchived($event, true)"
    />
  </TablePageLayout>
</template>
