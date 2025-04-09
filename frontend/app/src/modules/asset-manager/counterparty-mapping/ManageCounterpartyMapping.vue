<script setup lang="ts">
import type { CounterpartyMapping, CounterpartyMappingRequestPayload } from '@/modules/asset-manager/counterparty-mapping/schema';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import ManageCounterpartyMappingFormDialog
  from '@/modules/asset-manager/counterparty-mapping/ManageCounterpartyMappingFormDialog.vue';
import ManageCounterpartyMappingTable from '@/modules/asset-manager/counterparty-mapping/ManageCounterpartyMappingTable.vue';
import { useCounterpartyMappingApi } from '@/modules/asset-manager/counterparty-mapping/use-counterparty-mapping-api';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { omit } from 'es-toolkit';

const { t } = useI18n();
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
  fetchData,
  isLoading: loading,
  pagination,
  state,
} = usePaginationFilters<
  CounterpartyMapping,
  CounterpartyMappingRequestPayload
>(fetchAllCounterpartyMapping, {
  extraParams,
  history: 'router',
  onUpdateFilters(query) {
    set(selectedCounterparty, query.counterparty || '');
    set(selectedSymbol, query.counterpartySymbol || '');
  },
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

  await fetchData();
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

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

async function confirmDelete(mapping: CounterpartyMapping) {
  try {
    const success = await deleteCounterpartyMapping(omit(mapping, ['asset']));
    if (success)
      await fetchData();
  }
  catch (error: any) {
    setMessage({
      description: t('asset_management.cex_mapping.delete_error', {
        message: error.message,
      }),
    });
  }
}

function showDeleteConfirmation(item: CounterpartyMapping) {
  show(
    {
      message: t('asset_management.cex_mapping.confirm_delete.message', {
        asset: item.counterpartySymbol,
        location: item.counterparty.toUpperCase(),
      }),
      title: t('asset_management.counterparty_mapping.confirm_delete.title'),
    },
    async () => await confirmDelete(item),
  );
}
</script>

<template>
  <TablePageLayout child>
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        :loading="loading"
        @click="fetchData()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <RuiButton
        data-cy="managed-counterparty-mapping-add-btn"
        color="primary"
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
        :collection="state"
        :loading="loading"
        @refresh="fetchData()"
        @edit="edit($event)"
        @delete="showDeleteConfirmation($event)"
      />
      <ManageCounterpartyMappingFormDialog
        v-model="modelValue"
        :edit-mode="editMode"
        @refresh="fetchData()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
