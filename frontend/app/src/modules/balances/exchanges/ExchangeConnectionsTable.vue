<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { Exchange } from '@/modules/balances/types/exchanges';
import { type DataTableColumn, type DataTableSortColumn, RuiButton, RuiDataTable, RuiIcon, RuiSwitch } from '@rotki/ui-library';
import { externalLinks } from '@shared/external-links';
import { onBeforeMount } from 'vue';
import { useI18n } from 'vue-i18n';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useNonSyncingExchanges } from '@/modules/balances/exchanges/use-non-syncing-exchanges';
import { useLocations } from '@/modules/core/common/use-locations';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const sort = defineModel<DataTableSortColumn<Exchange>>('sort', { required: true });

defineProps<{
  rows: Exchange[];
  cols: DataTableColumn<Exchange>[];
  /** Whether the toolbar shows the hint on setting up an exchange just added. */
  showSetupHint: boolean;
  rowClass: (row: Exchange) => string;
  balanceOf: (row: Exchange) => BigNumber;
}>();

const emit = defineEmits<{
  'edit': [row: Exchange];
  'delete': [row: Exchange];
  'dismiss-setup-hint': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getExchangeName } = useLocations();
const { isNonSyncExchange, resetNonSyncingExchanges, toggleSync } = useNonSyncingExchanges();

/** What a row's delete button asks; `RowActions` adds the "Delete" label and the error tone. */
function deleteConfirm(item: Exchange): { message: string; title: string } {
  return {
    message: t('exchange_settings.confirmation.message', {
      location: getExchangeName(item.location),
      name: item.name,
    }),
    title: t('exchange_settings.confirmation.title'),
  };
}

onBeforeMount(() => {
  resetNonSyncingExchanges();
});
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <div
        v-if="showSetupHint"
        class="flex items-center gap-2 flex-1 min-w-0 text-sm text-rui-text-secondary"
        data-testid="exchange-setup-hint"
      >
        <RuiIcon
          name="lu-info"
          size="16"
          class="text-rui-info shrink-0"
        />
        <span class="min-w-0">{{ t('exchange_settings.setup_hint') }}</span>
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="shrink-0"
          :aria-label="t('common.actions.close')"
          @click="emit('dismiss-setup-hint')"
        >
          <RuiIcon
            name="lu-x"
            size="14"
          />
        </RuiButton>
      </div>
      <i18n-t
        v-else
        scope="global"
        keypath="exchange_settings.subtitle"
        tag="p"
        class="flex-1 min-w-0 text-sm text-rui-text-secondary"
      >
        <ExternalLink
          :text="t('exchange_settings.usage_guide')"
          :url="externalLinks.usageGuideSection.addingAnExchange"
        />
      </i18n-t>
    </template>

    <RuiDataTable
      v-model:sort="sort"
      row-attr="identifier"
      data-testid="exchange-table"
      :rows="rows"
      :cols="cols"
      :item-class="rowClass"
    >
      <template #item.location="{ row }">
        <LocationDisplay
          :identifier="row.location"
          horizontal
          size="24px"
        />
      </template>
      <template #item.syncEnabled="{ row }">
        <RuiSwitch
          color="primary"
          :model-value="!isNonSyncExchange(row)"
          details="hidden"
          @update:model-value="toggleSync(row)"
        />
      </template>
      <template #item.balance="{ row }">
        <FiatDisplay
          :value="balanceOf(row)"
          class="font-medium tabular-nums"
          data-testid="exchange-balance"
        />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          align="end"
          :delete-tooltip="t('exchange_settings.delete.tooltip')"
          :edit-tooltip="t('exchange_settings.edit.tooltip')"
          :delete-confirm="deleteConfirm(row)"
          @delete-click="emit('delete', row)"
          @edit-click="emit('edit', row)"
        />
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
