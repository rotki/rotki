<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { LocationAliases } from '@/modules/locations/use-location-tree-api';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { stringParam, toPillParams } from '@/modules/core/table/param-refs';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import LocationAliasFormDialog from '@/modules/locations/components/LocationAliasFormDialog.vue';
import { toLocationAliasFields } from '@/modules/locations/location-manager-fields';
import { onePage } from '@/modules/locations/location-rows';
import { useLocationAliases } from '@/modules/locations/use-location-aliases';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

type AliasRow = LocationAliases[number];

/** Whether the form for a new alias is open; the page's add button opens it. */
const adding = defineModel<boolean>('adding', { required: true });

const aliasSearch = ref<string>('');
const locationSearch = ref<string>('');
/** Why the aliases could not be loaded, until a later load succeeds. */
const loadFailure = shallowRef<string>();
/** Why the last removal failed, until the next one. */
const actionFailure = shallowRef<string>();
/** The alias whose row asks to confirm its deletion. */
const confirmingDelete = shallowRef<string>();

const { t } = useI18n({ useScope: 'global' });

const { pathLabelOf } = useLocationTreeStore();
const { aliases, loading, refreshAliases, removeAlias, saveAlias } = useLocationAliases();

/** The locations the saved aliases point at, offered by the location pill. */
const aliasLocations = computed<string[]>(() => [...new Set(get(aliases).map(entry => entry.locationIdentifier))]);

/** The aliases that match the filter: the alias as a substring, the location exactly. */
const rows = computed<AliasRow[]>(() => {
  const needle = get(aliasSearch).trim().toLowerCase();
  const location = get(locationSearch);
  return get(aliases).filter(entry => (needle === '' || entry.alias.toLowerCase().includes(needle))
    && (location === '' || entry.locationIdentifier === location));
});

/** Every alias on one page: there are rarely many, and a pager around a handful only adds noise. */
const allAliases = computed<TablePaginationData>(() => onePage(get(rows).length));

const filterFields = toLocationAliasFields(useSharedFieldResolvers(), t, (): string[] => get(aliasLocations));
const pillLabels = usePillBarLabels();
const filterParams = toPillParams({ alias: stringParam(aliasSearch), location: stringParam(locationSearch) });

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

const empty = computed<{ label: string; description?: string }>(() => {
  if (get(loadFailure))
    return { label: t('data_table.fetch_failed') };
  if (get(aliases).length > 0)
    return { label: t('location_manager.aliases.empty_search_label') };
  return { description: t('location_manager.aliases.empty_description'), label: t('location_manager.aliases.empty_label') };
});

async function remove(row: AliasRow): Promise<void> {
  set(confirmingDelete, undefined);
  set(actionFailure, undefined);
  const outcome = await removeAlias(row.alias);
  if (!outcome.ok)
    set(actionFailure, outcome.error);
}

onMounted(load);
</script>

<template>
  <TableFrame data-testid="location-aliases">
    <template #toolbar>
      <PillFilterBar
        v-model:params="filterParams"
        class="flex-1 min-w-64"
        :fields="filterFields"
        :labels="pillLabels"
      />
    </template>
    <RuiDataTable
      dense
      :rows="rows"
      :cols="cols"
      :loading="loading"
      :pagination="allAliases"
      :global-items-per-page="false"
      :empty="empty"
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
        <div
          v-if="confirmingDelete === row.alias"
          class="flex items-center gap-1"
          data-testid="location-alias-confirm"
        >
          <RuiButton
            size="sm"
            color="error"
            data-testid="location-alias-confirm-delete"
            @click="remove(row)"
          >
            {{ t('common.actions.delete') }}
          </RuiButton>
          <RuiButton
            size="sm"
            variant="text"
            data-testid="location-alias-cancel-delete"
            @click="confirmingDelete = undefined"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
        </div>
        <RuiButton
          v-else
          variant="text"
          icon
          size="sm"
          color="error"
          :title="t('common.actions.delete')"
          :aria-label="t('common.actions.delete')"
          data-testid="location-alias-delete"
          @click="confirmingDelete = row.alias"
        >
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </RuiButton>
      </template>
    </RuiDataTable>
    <LocationAliasFormDialog
      v-model="adding"
      :aliases="aliases"
      :save="saveAlias"
    />
  </TableFrame>
</template>
