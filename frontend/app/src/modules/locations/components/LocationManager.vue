<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { LocationFormData } from '@/modules/locations/location-form';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { startPromise } from '@shared/utils';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import LocationAliasesCard from '@/modules/locations/components/LocationAliasesCard.vue';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';
import LocationTreeFilter from '@/modules/locations/components/LocationTreeFilter.vue';
import LocationTreeRowActions from '@/modules/locations/components/LocationTreeRowActions.vue';
import LocationTreeRowName from '@/modules/locations/components/LocationTreeRowName.vue';
import LocationUsageNotice from '@/modules/locations/components/LocationUsageNotice.vue';
import { type LocationRow, locationRows, onePage } from '@/modules/locations/location-rows';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { useLocationTreeExpansion } from '@/modules/locations/use-location-tree-expansion';
import { ROOT_LOCATION, useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

type ManagerTab = 'locations' | 'aliases';

const search = ref<string>('');
const showArchived = ref<boolean>(false);
/** Locations archived on this visit, which stay listed so that restoring one is a click away. */
const archivedHere = ref<Set<string>>(new Set());
const formData = ref<LocationFormData>();
const addingAlias = ref<boolean>(false);
const blockedDeletion = ref<{ location: LocationNode; usage: Record<string, number> }>();
/** The unused location whose row asks before deleting it, until the user answers. */
const pendingDeletion = ref<LocationNode>();
const deleting = ref<boolean>(false);
/** Why the last archive, restore or deletion failed, until the next one. */
const actionFailure = shallowRef<string>();

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();
const router = useRouter();

const treeStore = useLocationTreeStore();
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
  set(blockedDeletion, undefined);
  set(pendingDeletion, undefined);
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
  set(blockedDeletion, undefined);
  set(pendingDeletion, undefined);
  const usage = await fetchUsage(location.identifier);
  if (!usage.ok) {
    set(actionFailure, usage.error);
    return;
  }
  if (!usage.value.deletable) {
    set(blockedDeletion, { location, usage: usage.value.usage });
    return;
  }
  set(pendingDeletion, location);
}

async function confirmDeletion(location: LocationNode): Promise<void> {
  set(deleting, true);
  const outcome = await deleteLocation(location.identifier);
  set(deleting, false);
  set(pendingDeletion, undefined);
  if (!outcome.ok)
    set(actionFailure, outcome.error);
}

/** A quick-add link adds to the tab it names, which clearing the link from the url would otherwise lose. */
const { consumeAddQuery } = useAddQuery((query) => {
  if (query.tab !== 'aliases')
    return addBelow(ROOT_LOCATION);
  set(tab, 'aliases');
  set(addingAlias, true);
});

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
        data-testid="location-manager-add"
        @click="addBelow(ROOT_LOCATION)"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('location_manager.actions.add') }}
      </RuiButton>
      <RuiButton
        v-else
        color="primary"
        size="lg"
        data-testid="location-manager-add"
        @click="addingAlias = true"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('location_manager.aliases.add') }}
      </RuiButton>
    </template>

    <template #tabs>
      <RuiTabs
        v-model="tab"
        color="primary"
        variant="segmented"
        data-testid="location-manager-tabs"
      >
        <RuiTab value="locations">
          {{ t('location_manager.tabs.locations') }}
        </RuiTab>
        <RuiTab value="aliases">
          {{ t('location_manager.tabs.aliases') }}
        </RuiTab>
      </RuiTabs>
    </template>

    <TableFrame v-if="tab === 'locations'">
      <template #toolbar>
        <LocationTreeFilter
          v-model:name="search"
          class="flex-1 min-w-64"
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
        hide-pagination
        row-attr="path"
        data-testid="location-manager-table"
      >
        <template
          v-if="actionFailure || blockedDeletion"
          #body.prepend
        >
          <tr v-if="actionFailure">
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
          <tr v-if="blockedDeletion">
            <td :colspan="cols.length">
              <LocationUsageNotice
                v-model="blockedDeletion"
                @archive="setArchived($event, true)"
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
          <InlineConfirm
            v-if="pendingDeletion?.identifier === row.node.identifier"
            class="my-1"
            tone="error"
            :title="t('location_manager.delete.title')"
            :message="t('location_manager.delete.message', { name: treeStore.pathLabelOf(row.node.identifier) })"
            :confirm-label="t('common.actions.delete')"
            :loading="deleting"
            data-testid="location-delete-confirm"
            @cancel="pendingDeletion = undefined"
            @confirm="confirmDeletion(row.node)"
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

    <KeepAlive>
      <LocationAliasesCard
        v-if="tab === 'aliases'"
        v-model:adding="addingAlias"
      />
    </KeepAlive>

    <LocationFormDialog
      v-model="formData"
      @saved="bringIntoView($event)"
    />
  </TablePageLayout>
</template>
