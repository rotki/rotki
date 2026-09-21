<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { LocationFormData } from '@/modules/locations/location-form';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import LocationAliasesCard from '@/modules/locations/components/LocationAliasesCard.vue';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';
import LocationUsageDialog from '@/modules/locations/components/LocationUsageDialog.vue';
import { type LocationRow, locationRows } from '@/modules/locations/location-rows';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { ROOT_LOCATION, useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const search = ref<string>('');
const showArchived = ref<boolean>(false);
const formData = ref<LocationFormData>();
const blockedDeletion = ref<{ location: LocationNode; usage: Record<string, number> }>();

const { t } = useI18n({ useScope: 'global' });

const treeStore = useLocationTreeStore();
const { show } = useConfirmStore();
const { setMessage } = useMessageStore();
const { deleteLocation, editLocation, fetchUsage } = useLocationManagement();

const rows = computed<LocationRow[]>(() => locationRows({
  childrenOf: treeStore.childrenOf,
  root: ROOT_LOCATION,
  search: get(search),
  showArchived: get(showArchived),
}));

const cols = computed<DataTableColumn<LocationRow>[]>(() => [{
  key: 'name',
  label: t('common.name'),
}, {
  cellClass: 'w-40',
  key: 'actions',
  label: t('common.actions_text'),
}]);

function reportFailure(message: string): void {
  setMessage({ description: message, title: t('location_manager.error') });
}

function addBelow(parentIdentifier: string): void {
  set(formData, { mode: 'add', parentIdentifier });
}

async function setArchived(location: LocationNode, archived: boolean): Promise<void> {
  const outcome = await editLocation(location.identifier, { isActive: !archived });
  if (!outcome.ok)
    reportFailure(outcome.error);
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
    message: t('location_manager.delete.message', { name: location.name }),
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

    <RuiCard :class-names="{ content: 'flex flex-col gap-4' }">
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
        row-attr="path"
        data-testid="location-manager-table"
      >
        <template #item.name="{ row }">
          <div
            class="flex items-center gap-2"
            :style="{ paddingLeft: `${row.depth * 1.5}rem` }"
            data-testid="location-row"
            :data-location="row.node.identifier"
          >
            <LocationIcon
              :item="row.node.identifier"
              horizontal
              size="20px"
              :class="{ 'opacity-50': !row.node.isActive }"
            />
            <RuiChip
              v-if="!row.node.isActive"
              size="sm"
              color="warning"
            >
              {{ t('location_manager.archived') }}
            </RuiChip>
            <RuiChip
              v-else-if="!row.node.isBuiltin"
              size="sm"
              color="primary"
              variant="outlined"
            >
              {{ t('location_manager.custom') }}
            </RuiChip>
          </div>
        </template>
        <template #item.actions="{ row }">
          <div class="flex items-center">
            <RuiButton
              v-if="row.node.isActive"
              variant="text"
              icon
              size="sm"
              :title="t('location_manager.actions.add_child')"
              data-testid="location-add-child"
              @click="addBelow(row.node.identifier)"
            >
              <RuiIcon
                name="lu-plus"
                size="16"
              />
            </RuiButton>
            <template v-if="!row.node.isBuiltin">
              <RuiButton
                variant="text"
                icon
                size="sm"
                :title="row.node.isActive ? t('location_manager.actions.archive') : t('location_manager.actions.unarchive')"
                data-testid="location-toggle-archive"
                @click="setArchived(row.node, row.node.isActive)"
              >
                <RuiIcon
                  :name="row.node.isActive ? 'lu-archive' : 'lu-archive-restore'"
                  size="16"
                />
              </RuiButton>
              <RowActions
                @edit-click="formData = { mode: 'edit', location: row.node }"
                @delete-click="requestDeletion(row.node)"
              />
            </template>
          </div>
        </template>
      </RuiDataTable>
    </RuiCard>

    <LocationAliasesCard />

    <LocationFormDialog v-model="formData" />
    <LocationUsageDialog
      v-model="blockedDeletion"
      @archive="setArchived($event, true)"
    />
  </TablePageLayout>
</template>
