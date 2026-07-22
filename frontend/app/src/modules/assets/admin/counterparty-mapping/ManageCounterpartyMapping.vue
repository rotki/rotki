<script setup lang="ts">
import type { CounterpartyMapping, CounterpartyMappingRequestPayload } from '@/modules/assets/admin/counterparty-mapping/schema';
import { omit } from 'es-toolkit';
import ManageCounterpartyMappingFormDialog
  from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingFormDialog.vue';
import ManageCounterpartyMappingTable from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingTable.vue';
import { useCounterpartyMappingApi } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { deleteCounterpartyMapping, fetchAllCounterpartyMapping } = useCounterpartyMappingApi();

const selectedCounterparty = ref<string>('');
const selectedSymbol = ref<string>('');
const editMode = ref<boolean>(false);

const modelValue = ref<CounterpartyMapping>();

const extraParams = computed(() => {
  const counterparty = get(selectedCounterparty);
  const symbol = get(selectedSymbol);
  const data: { counterparty?: string; counterpartySymbol?: string } = {};
  if (counterparty)
    data.counterparty = counterparty;
  if (symbol)
    data.counterpartySymbol = symbol;
  return data;
});

const {
  collection,
  isLoading: loading,
  pagination,
  refetch,
} = useServerTable<
  CounterpartyMapping,
  CounterpartyMappingRequestPayload
>({
  fetch: fetchAllCounterpartyMapping,
  params: [{
    fromQuery(query): void {
      set(selectedCounterparty, query.counterparty || '');
      set(selectedSymbol, query.counterpartySymbol || '');
    },
    to: 'both',
    values: extraParams,
  }],
  urlState: { mode: 'route' },
});

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    await router.replace({ query: {} });
    add({
      counterparty: (query.counterparty as string) || '',
      counterpartySymbol: (query.counterpartySymbol as string) || '',
    });
  }

  await refetch();
});

function add(payload?: Partial<CounterpartyMapping>) {
  set(modelValue, {
    asset: '',
    counterparty: get(selectedCounterparty) || '',
    counterpartySymbol: get(selectedSymbol) || '',
    ...payload,
  });
  set(editMode, false);
}

function edit(editMapping: CounterpartyMapping) {
  set(modelValue, editMapping);
  set(editMode, true);
}

const { showDeleteConfirmation } = useTableRowDeletion<CounterpartyMapping>({
  confirm: item => ({
    message: t('asset_management.cex_mapping.confirm_delete.message', {
      asset: item.counterpartySymbol,
      location: item.counterparty.toUpperCase(),
    }),
    title: t('asset_management.counterparty_mapping.confirm_delete.title'),
  }),
  deleteItem: mapping => deleteCounterpartyMapping(omit(mapping, ['asset'])),
  errorMessage: (_item, error) => t('asset_management.cex_mapping.delete_error', {
    message: getErrorMessage(error),
  }),
  onDeleted: refetch,
});
</script>

<template>
  <TablePageLayout child>
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        size="lg"
        :loading="loading"
        @click="refetch()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <RuiButton
        data-cy="managed-counterparty-mapping-add-btn"
        color="primary"
        size="lg"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('asset_management.cex_mapping.add_mapping') }}
      </RuiButton>
    </template>
    <RuiCard>
      <ManageCounterpartyMappingTable
        v-model:counterparty="selectedCounterparty"
        v-model:symbol="selectedSymbol"
        v-model:pagination="pagination"
        :collection="collection"
        :loading="loading"
        @refresh="refetch()"
        @edit="edit($event)"
        @delete="showDeleteConfirmation($event)"
      />
      <ManageCounterpartyMappingFormDialog
        v-model="modelValue"
        :edit-mode="editMode"
        @refresh="refetch()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
