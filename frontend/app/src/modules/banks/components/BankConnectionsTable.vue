<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { BankConnection } from '@/modules/banks/types';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { type DataTableColumn, type DataTableSortColumn, RuiDataTable } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import BankConnectionActions from '@/modules/banks/components/BankConnectionActions.vue';
import BankConnectorIcon from '@/modules/banks/components/BankConnectorIcon.vue';
import BankSyncStatus from '@/modules/banks/components/BankSyncStatus.vue';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const sort = defineModel<DataTableSortColumn<BankConnection>>('sort', { required: true });

defineProps<{
  rows: BankConnection[];
  cols: DataTableColumn<BankConnection>[];
  /** Why the connections could not be loaded, if the last load failed. */
  error?: unknown;
  rowClass: (row: BankConnection) => string;
  balanceOf: (row: BankConnection) => BigNumber;
  isSyncing: (row: BankConnection) => boolean;
}>();

const emit = defineEmits<{
  authenticate: [row: BankConnection];
  sync: [row: BankConnection];
  edit: [row: BankConnection];
  delete: [row: BankConnection];
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const failureMessage = useFailureMessage();

/** What a row's delete button asks; a failed removal is named above the table. */
function removeConfirm(row: BankConnection): RowDeleteQuestion {
  return {
    message: t('bank_settings.confirmation.message', { bank: row.displayName, name: row.name }),
    title: t('bank_settings.confirmation.title'),
  };
}
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <p class="text-sm text-rui-text-secondary m-0">
        {{ t('bank_settings.subtitle') }}
      </p>
    </template>
    <RuiDataTable
      v-model:sort="sort"
      row-attr="identifier"
      data-testid="bank-table"
      :rows="rows"
      :cols="cols"
      :item-class="rowClass"
      :empty="{ label: t('data_table.fetch_failed') }"
    >
      <template
        v-if="error"
        #empty-description
      >
        <TableFailureDescription
          :message="failureMessage(error)"
          :failure="error"
          @retry="emit('retry')"
        />
      </template>
      <template
        v-if="error && rows.length > 0"
        #body.prepend
      >
        <tr>
          <td :colspan="cols.length">
            <FailureStrip
              in-table
              :title="t('bank_settings.connections_failed')"
              :failure="error"
              data-testid="bank-connections-error"
              @retry="emit('retry')"
            />
          </td>
        </tr>
      </template>
      <template #item.connector="{ row }">
        <div class="flex items-center gap-2">
          <BankConnectorIcon
            :connector="row.connector"
            :bank-code="row.bankCode"
          />
          <span>{{ row.displayName }}</span>
        </div>
      </template>
      <template #item.name="{ row }">
        <span
          class="font-medium"
          data-testid="bank-connection-name"
        >
          {{ row.name }}
        </span>
      </template>
      <template #item.syncStatus="{ row }">
        <BankSyncStatus :status="row.syncStatus" />
      </template>
      <template #item.balance="{ row }">
        <FiatDisplay
          :value="balanceOf(row)"
          class="font-medium tabular-nums"
          data-testid="bank-balance"
        />
      </template>
      <template #item.actions="{ row }">
        <BankConnectionActions
          :authentication-required="!!row.syncStatus.authChallenge"
          :syncing="isSyncing(row)"
          :delete-confirm="removeConfirm(row)"
          @authenticate="emit('authenticate', row)"
          @sync="emit('sync', row)"
          @edit="emit('edit', row)"
          @delete="emit('delete', row)"
        />
      </template>
    </RuiDataTable>
  </TableFrame>
</template>
