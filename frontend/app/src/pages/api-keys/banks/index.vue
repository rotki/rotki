<script setup lang="ts">
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { BankAuthenticationRequest, BankConnection, BankFormData } from '@/modules/banks/types';
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { createNewBank, emptyCredentials, type NewBankRequest } from '@/modules/banks/bank-connection-form';
import BankAuthenticationDialog from '@/modules/banks/components/BankAuthenticationDialog.vue';
import BankConnectionActions from '@/modules/banks/components/BankConnectionActions.vue';
import BankConnectionFormDialog from '@/modules/banks/components/BankConnectionFormDialog.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys_sub.banks'), icon: 'lu-landmark', parent: '/api-keys/', order: 25, drawer: 'api-keys-banks', addAction: { labelKey: msg.$t('bank_settings.dialog.add.title') } },
  },
});

const bank = ref<BankFormData>();
const authentication = ref<BankAuthenticationRequest>();
/** The identifier of the connection a link asked to authenticate. */
const requestedAuthentication = ref<string>();
const syncing = ref<string[]>([]);
const sort = ref<DataTableSortColumn<BankConnection>>({
  column: 'name',
  direction: 'asc',
});

const { connections: rows, connectionsError, manifests, manifestsError } = storeToRefs(useBankConnectionsStore());
const { manifestFor } = useBankConnectionsStore();
const { refreshBankConnections, refreshSupportedBanks, removeBank, syncBanks } = useBanks();
const { show } = useConfirmStore();
const failureMessage = useFailureMessage();

const { t } = useI18n({ useScope: 'global' });

const router = useRouter();
const route = useRoute('/api-keys/banks/');

const cols = computed<DataTableColumn<BankConnection>[]>(() => [{
  cellClass: 'w-48',
  key: 'location',
  label: t('common.location'),
  sortable: true,
}, {
  key: 'name',
  label: t('common.name'),
  sortable: true,
}, {
  key: 'displayName',
  label: t('bank_settings.header.connector'),
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

const { highlight, rowClass } = useRowHighlight<{ identifier: string }>(({ identifier }) => identifier);

function rowKey(row: BankConnection): string {
  return row.identifier;
}

function isSyncing(row: BankConnection): boolean {
  return get(syncing).includes(rowKey(row)) || row.syncStatus.running;
}

function addBank(request?: NewBankRequest): void {
  set(bank, createNewBank(get(manifests), request));
}

function editBank(row: BankConnection): void {
  set(bank, {
    connector: row.connector,
    credentials: emptyCredentials(manifestFor(row.connector)),
    identifier: row.identifier,
    location: row.location,
    mode: 'edit',
    name: row.name,
    newName: row.name,
  });
}

function authenticate(row: BankConnection): void {
  if (row.syncStatus.authChallenge) {
    set(authentication, {
      challenge: row.syncStatus.authChallenge,
      identifier: row.identifier,
      location: row.location,
      name: row.name,
    });
  }
}

/**
 * Opens the authentication a link asked for, once that connection is listed.
 *
 * @remarks
 * The link can arrive before the connection list has loaded, so the request is held until the row
 * exists. A connection whose challenge was already answered opens nothing.
 */
function openRequestedAuthentication([requested, connections]: [string | undefined, BankConnection[]]): void {
  if (!requested)
    return;
  const row = connections.find(connection => connection.identifier === requested);
  if (!row)
    return;
  authenticate(row);
  set(requestedAuthentication, undefined);
}

async function sync(row: BankConnection): Promise<void> {
  set(syncing, [...get(syncing), rowKey(row)]);
  try {
    await syncBanks({ identifier: row.identifier });
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
    // a link can land before the supported banks have loaded; the form needs them to preselect a bank
    if (get(manifests).length === 0)
      await refreshSupportedBanks();
    addBank({
      connector: typeof query.connector === 'string' ? query.connector : undefined,
      location: typeof query.location === 'string' ? query.location : undefined,
    });
    await router.replace({ query: {} });
  }
  else if (typeof query.authenticate === 'string') {
    set(requestedAuthentication, query.authenticate);
    await router.replace({ query: {} });
  }
}, { immediate: true });

watch([requestedAuthentication, rows], openRequestedAuthentication, { immediate: true });
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

    <FailureStrip
      v-if="manifestsError && manifests.length === 0"
      class="mb-4"
      :title="t('bank_settings.supported_failed')"
      :failure="manifestsError"
      data-testid="bank-manifests-error"
      @retry="refreshSupportedBanks()"
    />

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
        :empty="connectionsError ? { label: t('data_table.fetch_failed') } : { description: t('bank_settings.empty') }"
      >
        <template
          v-if="connectionsError"
          #empty-description
        >
          <TableFailureDescription
            :message="failureMessage(connectionsError)"
            @retry="refreshBankConnections()"
          />
        </template>
        <template
          v-if="connectionsError && rows.length > 0"
          #body.prepend
        >
          <tr>
            <td :colspan="cols.length">
              <FailureStrip
                in-table
                :title="t('bank_settings.connections_failed')"
                :failure="connectionsError"
                data-testid="bank-connections-error"
                @retry="refreshBankConnections()"
              />
            </td>
          </tr>
        </template>
        <template #item.location="{ row }">
          <div class="flex items-center gap-2">
            <LocationIcon
              :item="row.location"
              icon
              size="20px"
            />
            <span>{{ row.displayName }}</span>
          </div>
        </template>
        <template #item.syncStatus="{ row }">
          <div class="flex flex-col items-start gap-1">
            <TimeAgoDisplay
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
              v-if="row.syncStatus.authChallenge"
              color="error"
              variant="tonal"
              size="sm"
              data-testid="bank-auth-required"
            >
              {{ t('bank_settings.sync.authentication_required') }}
            </RuiChip>
            <RuiChip
              v-else-if="row.syncStatus.authExpired"
              color="warning"
              variant="tonal"
              size="sm"
              data-testid="bank-auth-expired"
            >
              {{ t('bank_settings.sync.authentication_expired') }}
            </RuiChip>
            <template v-else-if="row.syncStatus.lastError">
              <RuiChip
                color="error"
                variant="tonal"
                size="sm"
                data-testid="bank-sync-error"
              >
                {{ t('bank_settings.sync.failed') }}
              </RuiChip>
              <span
                class="text-caption text-rui-text-secondary whitespace-normal"
                data-testid="bank-sync-error-message"
              >
                {{ row.syncStatus.lastError }}
              </span>
            </template>
          </div>
        </template>
        <template #item.actions="{ row }">
          <BankConnectionActions
            :authentication-required="!!row.syncStatus.authChallenge"
            :syncing="isSyncing(row)"
            @authenticate="authenticate(row)"
            @sync="sync(row)"
            @edit="editBank(row)"
            @delete="showRemoveConfirmation(row)"
          />
        </template>
      </RuiDataTable>
    </TableFrame>

    <BankConnectionFormDialog
      v-model="bank"
      @added="highlight($event)"
    />
    <BankAuthenticationDialog v-model="authentication" />
  </TablePageLayout>
</template>
