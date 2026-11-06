<script setup lang="ts">
import type { CounterpartyMapping, CounterpartyMappingRequestPayload } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { omit } from 'es-toolkit';
import { CounterpartyMappingFilterKeys, type Filters } from '@/modules/assets/admin/counterparty-mapping/counterparty-mapping-filter-keys';
import ManageCounterpartyMappingFormDialog
  from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingFormDialog.vue';
import ManageCounterpartyMappingTable from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingTable.vue';
import { useCounterpartyMappingApi } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-api';
import { useCounterpartyMappingFields } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-fields';
import MappingAdminLayout from '@/modules/assets/admin/MappingAdminLayout.vue';
import { useMappingAdmin } from '@/modules/assets/admin/use-mapping-admin';
import { fromRequest } from '@/modules/core/api/request-result';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const { t } = useI18n({ useScope: 'global' });

const { deleteCounterpartyMapping, fetchAllCounterpartyMapping } = useCounterpartyMappingApi();

const fields = useCounterpartyMappingFields();

const {
  collection,
  filter,
  isLoading: loading,
  pagination,
  refetch,
} = useServerTable<
  CounterpartyMapping,
  CounterpartyMappingRequestPayload,
  Filters
>({
  fetch: async payload => fromRequest(async () => fetchAllCounterpartyMapping(payload)),
  fields,
  urlState: { mode: 'route' },
});

const { add, consumeAddQuery, edit, editMode, modelValue } = useMappingAdmin<CounterpartyMapping, Filters>({
  blank: () => ({ asset: '', counterparty: '', counterpartySymbol: '' }),
  filter,
  seedFromFilter: {
    counterparty: CounterpartyMappingFilterKeys.COUNTERPARTY,
    counterpartySymbol: CounterpartyMappingFilterKeys.COUNTERPARTY_SYMBOL,
  },
  seedFromQuery: { counterparty: 'counterparty', counterpartySymbol: 'counterpartySymbol' },
});

onMounted(async () => {
  await consumeAddQuery();
  await refetch();
});

function deleteConfirm(item: CounterpartyMapping): RowDeleteQuestion {
  return {
    message: t('asset_management.cex_mapping.confirm_delete.message', {
      asset: item.counterpartySymbol,
      location: item.counterparty.toUpperCase(),
    }),
    title: t('asset_management.counterparty_mapping.confirm_delete.title'),
  };
}

const { deleteRow, failure: deleteFailure } = useTableRowDeletion<CounterpartyMapping>({
  deleteItem: mapping => deleteCounterpartyMapping(omit(mapping, ['asset'])),
  failureTitle: () => t('asset_management.cex_mapping.delete_error'),
  onDeleted: refetch,
});
</script>

<template>
  <MappingAdminLayout
    :loading="loading"
    add-test-id="managed-counterparty-mapping-add-btn"
    :add-label="t('asset_management.cex_mapping.add_mapping')"
    @refresh="refetch()"
    @add="add()"
  >
    <FailureStrip
      v-if="deleteFailure"
      class="mb-4"
      :title="deleteFailure.title"
      :failure="deleteFailure.failure"
      data-testid="counterparty-mapping-delete-error"
    />
    <ManageCounterpartyMappingTable
      v-model:filters="filter"
      v-model:pagination="pagination"
      :collection="collection"
      :fields="fields"
      :loading="loading"
      :delete-confirm="deleteConfirm"
      @edit="edit($event)"
      @delete="deleteRow($event)"
    />
    <ManageCounterpartyMappingFormDialog
      v-model="modelValue"
      :edit-mode="editMode"
      @refresh="refetch()"
    />
  </MappingAdminLayout>
</template>
