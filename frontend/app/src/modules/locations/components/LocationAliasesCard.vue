<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { LocationAliases } from '@/modules/locations/use-location-tree-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useLocationAliases } from '@/modules/locations/use-location-aliases';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

type AliasRow = LocationAliases[number];

const alias = ref<string>('');
const target = ref<string>('');

const { t } = useI18n({ useScope: 'global' });

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();
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

function reportFailure(message: string): void {
  setMessage({ description: message, title: t('location_manager.aliases.error') });
}

async function save(): Promise<void> {
  if (!get(canSave))
    return;
  const outcome = await saveAlias(get(alias), get(target));
  if (!outcome.ok)
    return reportFailure(outcome.error);
  set(alias, '');
  set(target, '');
}

function remove(row: AliasRow): void {
  show({
    message: t('location_manager.aliases.delete_message', { alias: row.alias, location: pathLabelOf(row.locationIdentifier) }),
    primaryAction: t('common.actions.delete'),
    title: t('location_manager.aliases.delete_title'),
  }, async () => {
    const outcome = await removeAlias(row.alias);
    if (!outcome.ok)
      reportFailure(outcome.error);
  });
}

onMounted(async () => {
  const outcome = await refreshAliases();
  if (!outcome.ok)
    reportFailure(outcome.error);
});
</script>

<template>
  <RuiCard
    :class-names="{ content: 'flex flex-col gap-4' }"
    data-testid="location-aliases"
  >
    <template #header>
      {{ t('location_manager.aliases.title') }}
    </template>
    <template #subheader>
      {{ t('location_manager.aliases.subtitle') }}
    </template>
    <form
      class="flex flex-col sm:flex-row sm:items-center gap-4"
      data-testid="location-alias-form"
      @submit.prevent="save()"
    >
      <RuiTextField
        v-model="alias"
        class="sm:basis-1/3"
        variant="outlined"
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
    <RuiDataTable
      dense
      outlined
      :rows="aliases"
      :cols="cols"
      :loading="loading"
      :pagination="allAliases"
      :global-items-per-page="false"
      :empty="{ label: t('location_manager.aliases.empty_label'), description: t('location_manager.aliases.empty_description') }"
      hide-default-header
      hide-default-footer
      row-attr="alias"
      data-testid="location-aliases-table"
    >
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
  </RuiCard>
</template>
