<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { LocationAliases } from '@/modules/locations/use-location-tree-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useLocationAliases } from '@/modules/locations/use-location-aliases';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

type AliasRow = LocationAliases[number];

const alias = ref<string>('');
const target = ref<string>('');
/** Why the aliases could not be loaded, until a later load succeeds. */
const loadFailure = shallowRef<string>();
/** Why the last save or removal failed, until the next one. */
const actionFailure = shallowRef<string>();

const { t } = useI18n({ useScope: 'global' });

const { show } = useConfirmStore();
const { pathLabelOf } = useLocationTreeStore();
const { aliases, loading, refreshAliases, removeAlias, saveAlias } = useLocationAliases();

const canSave = computed<boolean>(() => get(alias).trim() !== '' && get(target) !== '');

/** Every alias on one page: there are rarely many, and a pager around a handful only adds noise. */
const allAliases = computed<TablePaginationData>(() => {
  const total = get(aliases).length;
  return { limit: Math.max(total, 1), page: 1, total };
});

const cols = computed<DataTableColumn<AliasRow>[]>(() => [{
  key: 'alias',
  label: t('location_manager.aliases.alias'),
}, {
  key: 'locationIdentifier',
  label: t('common.location'),
}, {
  cellClass: 'w-px',
  key: 'actions',
  label: t('common.actions_text'),
}]);

async function load(): Promise<void> {
  const outcome = await refreshAliases();
  set(loadFailure, outcome.ok ? undefined : outcome.error);
}

async function save(): Promise<void> {
  if (!get(canSave))
    return;
  set(actionFailure, undefined);
  const outcome = await saveAlias(get(alias), get(target));
  if (!outcome.ok)
    return set(actionFailure, outcome.error);
  set(alias, '');
  set(target, '');
}

function remove(row: AliasRow): void {
  show({
    message: t('location_manager.aliases.delete_message', { alias: row.alias, location: pathLabelOf(row.locationIdentifier) }),
    primaryAction: t('common.actions.delete'),
    title: t('location_manager.aliases.delete_title'),
  }, async () => {
    set(actionFailure, undefined);
    const outcome = await removeAlias(row.alias);
    if (!outcome.ok)
      set(actionFailure, outcome.error);
  });
}

onMounted(async () => load());
</script>

<template>
  <TableFrame data-testid="location-aliases">
    <template #toolbar>
      <p class="text-sm text-rui-text-secondary m-0 basis-full">
        {{ t('location_manager.aliases.subtitle') }}
      </p>
      <form
        class="flex flex-col sm:flex-row sm:items-center gap-4 w-full"
        data-testid="location-alias-form"
        @submit.prevent="save()"
      >
        <RuiTextField
          v-model="alias"
          class="sm:basis-1/3"
          color="primary"
          dense
          :label="t('location_manager.aliases.alias')"
          hide-details
          data-testid="location-alias-name"
        />
        <LocationSelector
          v-model="target"
          class="sm:basis-1/2 grow"
          dense
          :label="t('common.location')"
          hide-details
          data-testid="location-alias-target"
        />
        <RuiButton
          type="submit"
          color="primary"
          :disabled="!canSave"
          data-testid="location-alias-save"
        >
          {{ t('location_manager.aliases.add') }}
        </RuiButton>
      </form>
    </template>
    <RuiDataTable
      dense
      :rows="aliases"
      :cols="cols"
      :loading="loading"
      :pagination="allAliases"
      :global-items-per-page="false"
      :empty="loadFailure ? { label: t('data_table.fetch_failed') } : { label: t('location_manager.aliases.empty_label'), description: t('location_manager.aliases.empty_description') }"
      hide-default-header
      hide-pagination
      row-attr="alias"
      data-testid="location-aliases-table"
    >
      <template
        v-if="loadFailure"
        #empty-description
      >
        <TableFailureDescription
          :message="loadFailure"
          @retry="load()"
        />
      </template>
      <template
        v-if="actionFailure || (loadFailure && aliases.length > 0)"
        #body.prepend
      >
        <tr v-if="actionFailure">
          <td :colspan="cols.length">
            <FailureStrip
              in-table
              :title="t('location_manager.aliases.error')"
              :failure="actionFailure"
              :retryable="false"
              data-testid="location-aliases-action-error"
            />
          </td>
        </tr>
        <tr v-if="loadFailure && aliases.length > 0">
          <td :colspan="cols.length">
            <FailureStrip
              in-table
              :title="t('location_manager.aliases.load_error')"
              :failure="loadFailure"
              data-testid="location-aliases-load-error"
              @retry="load()"
            />
          </td>
        </tr>
      </template>
      <template #item.locationIdentifier="{ row }">
        <div class="flex items-center gap-2 min-w-0">
          <LocationIcon
            class="shrink-0"
            :item="row.locationIdentifier"
            icon
            size="20px"
          />
          <span class="truncate">{{ pathLabelOf(row.locationIdentifier) }}</span>
        </div>
      </template>
      <template #item.actions="{ row }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          color="error"
          :title="t('common.actions.delete')"
          :aria-label="t('common.actions.delete')"
          data-testid="location-alias-delete"
          @click="remove(row)"
        >
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </RuiButton>
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
