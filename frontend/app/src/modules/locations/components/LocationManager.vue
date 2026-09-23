<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { LocationFormData } from '@/modules/locations/location-form';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { startPromise } from '@shared/utils';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import LocationAliasesCard from '@/modules/locations/components/LocationAliasesCard.vue';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';
import LocationTreeRowActions from '@/modules/locations/components/LocationTreeRowActions.vue';
import LocationTreeRowName from '@/modules/locations/components/LocationTreeRowName.vue';
import LocationUsageDialog from '@/modules/locations/components/LocationUsageDialog.vue';
import { type LocationRow, locationRows } from '@/modules/locations/location-rows';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { useLocationTreeExpansion } from '@/modules/locations/use-location-tree-expansion';
import { ROOT_LOCATION, useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

type ManagerTab = 'locations' | 'aliases';

const search = ref<string>('');
const showArchived = ref<boolean>(false);
/** Locations archived on this visit, which stay listed so that restoring one is a click away. */
const archivedHere = ref<Set<string>>(new Set());
const formData = ref<LocationFormData>();
const blockedDeletion = ref<{ location: LocationNode; usage: Record<string, number> }>();

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();
const router = useRouter();

const treeStore = useLocationTreeStore();
const { show } = useConfirmStore();
const { setMessage } = useMessageStore();
const { deleteLocation, editLocation, fetchUsage } = useLocationManagement();
const { isExpanded, reveal, toggle } = useLocationTreeExpansion();
const { highlight, rowClass } = useRowHighlight<LocationRow>(row => row.node.identifier);

/** The open tab, kept in the url so a link can open the aliases directly. */
const tab = computed<ManagerTab>({
  get: () => (get(route).query.tab === 'aliases' ? 'aliases' : 'locations'),
  set: (value) => {
    startPromise(router.replace({ query: { ...get(route).query, tab: value === 'aliases' ? value : undefined } }));
  },
});

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

function reportFailure(message: string): void {
  setMessage({ description: message, title: t('location_manager.error') });
}

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
  const outcome = await editLocation(location.identifier, { isActive: !archived });
  if (!outcome.ok)
    return reportFailure(outcome.error);
  const kept = new Set(get(archivedHere));
  if (archived)
    kept.add(location.identifier);
  set(archivedHere, kept);
  await bringIntoView(location.identifier);
}

/** A used location can not be deleted; the user then sees what uses it and may archive it. */
async function requestDeletion(location: LocationNode): Promise<void> {
  const usage = await fetchUsage(location.identifier);
  if (!usage.ok)
    return reportFailure(usage.error);
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
      reportFailure(outcome.error);
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
        v-if="tab === 'locations'"
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

    <RuiTabs
      v-model="tab"
      color="primary"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
      data-testid="location-manager-tabs"
    >
      <RuiTab value="locations">
        {{ t('location_manager.tabs.locations') }}
      </RuiTab>
      <RuiTab value="aliases">
        {{ t('location_manager.tabs.aliases') }}
      </RuiTab>
    </RuiTabs>

    <RuiCard
      v-if="tab === 'locations'"
      :class-names="{ content: 'flex flex-col gap-4' }"
    >
      <div class="flex flex-wrap items-center gap-4">
        <RuiTextField
          v-model="search"
          class="grow"
          variant="outlined"
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
      </div>
      <RuiDataTable
        dense
        outlined
        :rows="rows"
        :cols="cols"
        :pagination="wholeTree"
        :global-items-per-page="false"
        :item-class="rowClass"
        :empty="empty"
        hide-default-header
        hide-default-footer
        row-attr="path"
        data-testid="location-manager-table"
      >
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
    </RuiCard>

    <LocationAliasesCard v-else />

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
