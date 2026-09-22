<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { LocationAliases } from '@/modules/locations/use-location-tree-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { useLocationAliases } from '@/modules/locations/use-location-aliases';

type AliasRow = LocationAliases[number];

const alias = ref<string>('');
const target = ref<string>('');

const { t } = useI18n({ useScope: 'global' });

const { setMessage } = useMessageStore();
const { aliases, loading, refreshAliases, removeAlias, saveAlias } = useLocationAliases();

const canSave = computed<boolean>(() => get(alias).trim() !== '' && get(target) !== '');

const cols = computed<DataTableColumn<AliasRow>[]>(() => [{
  key: 'alias',
  label: t('location_manager.aliases.alias'),
}, {
  key: 'locationIdentifier',
  label: t('common.location'),
}, {
  cellClass: 'w-20',
  key: 'actions',
  label: t('common.actions_text'),
}]);

function reportFailure(message: string): void {
  setMessage({ description: message, title: t('location_manager.aliases.error') });
}

async function save(): Promise<void> {
  const outcome = await saveAlias(get(alias), get(target));
  if (!outcome.ok)
    return reportFailure(outcome.error);
  set(alias, '');
  set(target, '');
}

async function remove(row: AliasRow): Promise<void> {
  const outcome = await removeAlias(row.alias);
  if (!outcome.ok)
    reportFailure(outcome.error);
}

onMounted(async () => {
  const outcome = await refreshAliases();
  if (!outcome.ok)
    reportFailure(outcome.error);
});
</script>

<template>
  <RuiCard
    class="mt-4"
    :class-names="{ content: 'flex flex-col gap-4' }"
    data-testid="location-aliases"
  >
    <template #header>
      {{ t('location_manager.aliases.title') }}
    </template>
    <template #subheader>
      {{ t('location_manager.aliases.subtitle') }}
    </template>
    <div class="flex flex-wrap items-start gap-4">
      <RuiTextField
        v-model="alias"
        class="grow"
        variant="outlined"
        color="primary"
        dense
        :label="t('location_manager.aliases.alias')"
        hide-details
        data-testid="location-alias-name"
      />
      <LocationSelector
        v-model="target"
        class="grow"
        dense
        :label="t('common.location')"
        hide-details
        data-testid="location-alias-target"
      />
      <RuiButton
        color="primary"
        :disabled="!canSave"
        data-testid="location-alias-save"
        @click="save()"
      >
        {{ t('common.actions.save') }}
      </RuiButton>
    </div>
    <RuiDataTable
      dense
      outlined
      :rows="aliases"
      :cols="cols"
      :loading="loading"
      row-attr="alias"
      data-testid="location-aliases-table"
    >
      <template #item.locationIdentifier="{ row }">
        <LocationDisplay
          :identifier="row.locationIdentifier"
          horizontal
          :open-details="false"
        />
      </template>
      <template #item.actions="{ row }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          color="error"
          :title="t('common.actions.delete')"
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
