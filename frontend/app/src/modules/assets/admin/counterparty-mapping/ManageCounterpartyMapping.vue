<script setup lang="ts">
import type { CounterpartyMapping, CounterpartyMappingRequestPayload } from '@/modules/assets/admin/counterparty-mapping/schema';
import { omit } from 'es-toolkit';
import ManageCounterpartyMappingFormDialog
  from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingFormDialog.vue';
import ManageCounterpartyMappingTable from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingTable.vue';
import { useCounterpartyMappingApi } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-api';
import { useCounterpartyMappingFields } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-fields';
import { type CounterpartyMappingFilterKey, CounterpartyMappingFilterKeys, type Filters } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-filter';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { firstQueryValue } from '@/modules/core/table/route';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { deleteCounterpartyMapping, fetchAllCounterpartyMapping } = useCounterpartyMappingApi();

const editMode = ref<boolean>(false);

const modelValue = ref<CounterpartyMapping>();

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
  fetch: fetchAllCounterpartyMapping,
  fields,
  urlState: { mode: 'route' },
});

/** The bag types every value as one-or-many; both of these fields are single-valued. */
function filterValue(key: CounterpartyMappingFilterKey): string {
  const picked = get(filter)[key];
  return (Array.isArray(picked) ? picked[0] : picked)?.toString() ?? '';
}

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    await router.replace({ query: {} });
    add({
      counterparty: firstQueryValue(query.counterparty),
      counterpartySymbol: firstQueryValue(query.counterpartySymbol),
    });
  }

  await refetch();
});

/**
 * Opens the mapping dialog on a new mapping, seeded from the filter bar.
 *
 * @remarks
 * The counterparty and its symbol default to whatever the bar is narrowed to, so adding a mapping
 * while filtered does not make the user pick the same values again; `payload` overrides them.
 */
function add(payload?: Partial<CounterpartyMapping>) {
  set(modelValue, {
    asset: '',
    counterparty: filterValue(CounterpartyMappingFilterKeys.COUNTERPARTY),
    counterpartySymbol: filterValue(CounterpartyMappingFilterKeys.COUNTERPARTY_SYMBOL),
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
        data-testid="managed-counterparty-mapping-add-btn"
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
        v-model:filters="filter"
        v-model:pagination="pagination"
        :collection="collection"
        :fields="fields"
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
