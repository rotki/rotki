<script setup lang="ts">
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { BankConnection, BankFormData } from '@/modules/banks/types';
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { emptyCredentials } from '@/modules/banks/bank-connection-form';
import BankConnectionActions from '@/modules/banks/components/BankConnectionActions.vue';
import BankConnectionFormDialog from '@/modules/banks/components/BankConnectionFormDialog.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys_sub.banks'), icon: 'lu-landmark', parent: '/api-keys/', order: 25, drawer: 'api-keys-banks', addAction: { labelKey: msg.$t('bank_settings.dialog.add.title') } },
  },
});

const bank = ref<BankFormData>();
const syncing = ref<string[]>([]);
const sort = ref<DataTableSortColumn<BankConnection>>({
  column: 'name',
  direction: 'asc',
});

const { connections: rows, manifests } = storeToRefs(useBankConnectionsStore());
const { manifestFor } = useBankConnectionsStore();
const { refreshBankConnections, refreshSupportedBanks, removeBank, syncBanks } = useBanks();
const { show } = useConfirmStore();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute('/api-keys/banks/');

const cols = computed<DataTableColumn<BankConnection>[]>(() => [{
  align: 'center',
  cellClass: 'py-0 w-32',
  key: 'location',
  label: t('common.location'),
  sortable: true,
}, {
  key: 'name',
  label: t('common.name'),
  sortable: true,
}, {
  key: 'syncStatus',
  label: t('bank_settings.header.last_sync'),
}, {
  align: 'center',
  cellClass: 'w-40',
  key: 'actions',
  label: t('common.actions_text'),
}]);

useRememberTableSorting<BankConnection>(TableId.BANKS, sort, cols);

const { highlight, rowClass } = useRowHighlight<{ location: string; name: string }>(
  ({ location, name }) => `${location}#${name}`,
);

function rowKey(row: BankConnection): string {
  return `${row.location}#${row.name}`;
}

function isSyncing(row: BankConnection): boolean {
  return get(syncing).includes(rowKey(row)) || row.syncStatus.running;
}

function createNewBank(): BankFormData {
  const location = get(manifests)[0]?.location ?? '';
  return {
    credentials: emptyCredentials(manifestFor(location)),
    location,
    mode: 'add',
    name: '',
    newName: '',
  };
}

function addBank(): void {
  set(bank, createNewBank());
}

function editBank(row: BankConnection): void {
  set(bank, {
    credentials: emptyCredentials(manifestFor(row.location)),
    location: row.location,
    mode: 'edit',
    name: row.name,
    newName: row.name,
  });
}

async function sync(row: BankConnection): Promise<void> {
  set(syncing, [...get(syncing), rowKey(row)]);
  try {
    await syncBanks({ location: row.location, name: row.name });
  }
  finally {
    set(syncing, get(syncing).filter(key => key !== rowKey(row)));
  }
}

function showRemoveConfirmation(row: BankConnection): void {
  show({
    message: t('bank_settings.confirmation.message', { bank: row.displayName, name: row.name }),
    title: t('bank_settings.confirmation.title'),
  }, async () => removeBank(row));
}

onBeforeMount(() => {
  startPromise(Promise.all([refreshSupportedBanks(), refreshBankConnections()]));
});

watch(route, async (route) => {
  const { query } = route;
  if (query.add) {
    addBank();
    await router.replace({ query: {} });
  }
}, { immediate: true });
</script>

<template>
  <TablePageLayout
    data-testid="banks"
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.banks'),
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        size="lg"
        data-testid="add-bank"
        :disabled="manifests.length === 0"
        @click="addBank()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('bank_settings.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <div class="text-sm text-rui-text-secondary mb-4">
        {{ t('bank_settings.subtitle') }}
      </div>
      <RuiDataTable
        v-model:sort="sort"
        outlined
        row-attr="name"
        data-testid="bank-table"
        :rows="rows"
        :cols="cols"
        :item-class="rowClass"
        :empty="{ description: t('bank_settings.empty') }"
      >
        <template #item.location="{ row }">
          <LocationDisplay :identifier="row.location" />
        </template>
        <template #item.syncStatus="{ row }">
          <div class="flex flex-col gap-1">
            <DateDisplay
              v-if="row.syncStatus.lastSyncTs"
              :timestamp="row.syncStatus.lastSyncTs"
            />
            <span
              v-else
              class="text-rui-text-secondary"
            >
              {{ t('bank_settings.sync.never') }}
            </span>
            <RuiChip
              v-if="row.syncStatus.lastError"
              color="error"
              size="sm"
              data-testid="bank-sync-error"
              :title="row.syncStatus.lastError"
            >
              {{ t('bank_settings.sync.failed') }}
            </RuiChip>
          </div>
        </template>
        <template #item.actions="{ row }">
          <BankConnectionActions
            :syncing="isSyncing(row)"
            @sync="sync(row)"
            @edit="editBank(row)"
            @delete="showRemoveConfirmation(row)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>

    <BankConnectionFormDialog
      v-model="bank"
      @added="highlight($event)"
    />
  </TablePageLayout>
</template>
