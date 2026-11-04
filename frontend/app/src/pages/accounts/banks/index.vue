<script setup lang="ts">
import type { BankAuthenticationRequest, BankConnection, BankConnectionIdentity, BankFormData } from '@/modules/banks/types';
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { emptyCredentials } from '@/modules/banks/bank-connection-form';
import BankAuthenticationDialog from '@/modules/banks/components/BankAuthenticationDialog.vue';
import BankBalancesEmpty from '@/modules/banks/components/BankBalancesEmpty.vue';
import BankConnectionActions from '@/modules/banks/components/BankConnectionActions.vue';
import BankConnectionFormDialog from '@/modules/banks/components/BankConnectionFormDialog.vue';
import BankConnectorIcon from '@/modules/banks/components/BankConnectorIcon.vue';
import BankSyncStatus from '@/modules/banks/components/BankSyncStatus.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankConnectionsTable } from '@/modules/banks/use-bank-connections-table';
import { useBanks } from '@/modules/banks/use-banks';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts_sub.banks'), icon: 'lu-landmark', parent: '/accounts/', heading: msg.$t('navigation_menu.accounts_sub.heading.exchanges_and_banks'), order: 70, drawer: 'accounts-banks', addAction: { labelKey: msg.$t('bank_settings.dialog.add.title') } },
  },
});

const bank = ref<BankFormData>();
const authentication = ref<BankAuthenticationRequest>();
const requestedAuthentication = ref<BankConnectionIdentity>();

const { canAddBank, connections: rows, connectionsError, manifests, manifestsError } = storeToRefs(useBankConnectionsStore());
const { manifestFor } = useBankConnectionsStore();
const { refreshBankConnections, refreshSupportedBanks, removeBank, syncBanks } = useBanks();
const { show } = useConfirmStore();
const failureMessage = useFailureMessage();

const { t } = useI18n({ useScope: 'global' });

const router = useRouter();
const route = useRoute('/accounts/banks/');

const { balanceOf, cols, highlight, isSyncing, modelSort: sort, rowClass, whileSyncing } = useBankConnectionsTable();

function createNewBank(requested?: string): BankFormData {
  const connector = (requested && manifestFor(requested)) ? requested : get(manifests)[0]?.connector ?? '';
  return {
    connector,
    credentials: emptyCredentials(manifestFor(connector)),
    mode: 'add',
    name: '',
    newName: '',
  };
}

function addBank(connector?: string): void {
  set(bank, createNewBank(connector));
}

function editBank(row: BankConnection): void {
  set(bank, {
    connector: row.connector,
    credentials: emptyCredentials(manifestFor(row.connector)),
    mode: 'edit',
    name: row.name,
    newName: row.name,
  });
}

function authenticate(row: BankConnection): void {
  if (row.syncStatus.authChallenge) {
    set(authentication, {
      challenge: row.syncStatus.authChallenge,
      connector: row.connector,
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
function openRequestedAuthentication([requested, connections]: [BankConnectionIdentity | undefined, BankConnection[]]): void {
  if (!requested)
    return;
  const row = connections.find(connection => connection.connector === requested.connector && connection.name === requested.name);
  if (!row)
    return;
  authenticate(row);
  set(requestedAuthentication, undefined);
}

async function sync(row: BankConnection): Promise<void> {
  await whileSyncing(row, async () => syncBanks({ connector: row.connector, name: row.name }));
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
    addBank(typeof query.connector === 'string' ? query.connector : undefined);
    await router.replace({ query: {} });
  }
  else if (typeof query.authenticate === 'string' && typeof query.connector === 'string') {
    set(requestedAuthentication, { connector: query.connector, name: query.authenticate });
    await router.replace({ query: {} });
  }
}, { immediate: true });

watch([requestedAuthentication, rows], openRequestedAuthentication, { immediate: true });
</script>

<template>
  <TablePageLayout
    data-testid="banks"
    :title="[
      t('navigation_menu.accounts'),
      t('navigation_menu.accounts_sub.banks'),
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        data-testid="add-bank"
        :disabled="!canAddBank"
        @click="addBank()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('bank_balances.add_bank') }}
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

    <BankBalancesEmpty
      v-if="rows.length === 0 && !connectionsError"
      @connect="addBank($event)"
    />

    <TableFrame v-else>
      <template #toolbar>
        <p class="text-sm text-rui-text-secondary m-0">
          {{ t('bank_settings.subtitle') }}
        </p>
      </template>
      <RuiDataTable
        v-model:sort="sort"
        row-attr="name"
        data-testid="bank-table"
        :rows="rows"
        :cols="cols"
        :item-class="rowClass"
        :empty="{ label: t('data_table.fetch_failed') }"
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
