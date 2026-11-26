<script setup lang="ts">
import type { BankAuthenticationRequest, BankConnection, BankFormData } from '@/modules/banks/types';
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { onBeforeMount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import { createNewBank, emptyCredentials } from '@/modules/banks/bank-connection-form';
import BankAuthenticationDialog from '@/modules/banks/components/BankAuthenticationDialog.vue';
import BankBalancesEmpty from '@/modules/banks/components/BankBalancesEmpty.vue';
import BankConnectionFormDialog from '@/modules/banks/components/BankConnectionFormDialog.vue';
import BankConnectionsTable from '@/modules/banks/components/BankConnectionsTable.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankConnectionsTable } from '@/modules/banks/use-bank-connections-table';
import { useBanks } from '@/modules/banks/use-banks';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.accounts_sub.banks'), icon: 'lu-landmark', parent: '/accounts/', heading: msg.$t('navigation_menu.accounts_sub.heading.exchanges_and_banks'), order: 70, drawer: 'accounts-banks', addAction: { labelKey: msg.$t('bank_settings.dialog.add.title') } },
  },
});

const bank = ref<BankFormData>();
const authentication = ref<BankAuthenticationRequest>();
/** The identifier of the connection a link asked to authenticate. */
const requestedAuthentication = ref<string>();

const { canAddBank, connections: rows, connectionsError, manifests, manifestsError } = storeToRefs(useBankConnectionsStore());
const { manifestFor } = useBankConnectionsStore();
const { refreshBankConnections, refreshSupportedBanks, removeBank, syncBanks } = useBanks();

const { t } = useI18n({ useScope: 'global' });

const router = useRouter();
const route = useRoute('/accounts/banks/');

const { balanceOf, cols, highlight, isSyncing, modelSort: sort, removeFailure, removeRow, rowClass, whileSyncing } = useBankConnectionsTable(removeBank);

function addBank(connector?: string): void {
  set(bank, createNewBank(get(manifests), connector));
}

function editBank(row: BankConnection): void {
  set(bank, {
    connector: row.connector,
    credentials: emptyCredentials(manifestFor(row.connector)),
    identifier: row.identifier,
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
      identifier: row.identifier,
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
  await whileSyncing(row, async () => syncBanks({ identifier: row.identifier }));
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

    <FailureStrip
      v-if="removeFailure"
      class="mb-4"
      :title="removeFailure.title"
      :failure="removeFailure.failure"
      data-testid="bank-remove-error"
    />

    <BankBalancesEmpty
      v-if="rows.length === 0 && !connectionsError"
      @connect="addBank($event)"
    />

    <BankConnectionsTable
      v-else
      v-model:sort="sort"
      :rows="rows"
      :cols="cols"
      :error="connectionsError"
      :row-class="rowClass"
      :balance-of="balanceOf"
      :is-syncing="isSyncing"
      @authenticate="authenticate($event)"
      @sync="sync($event)"
      @edit="editBank($event)"
      @delete="removeRow($event)"
      @retry="refreshBankConnections()"
    />

    <BankConnectionFormDialog
      v-model="bank"
      @added="highlight($event)"
    />
    <BankAuthenticationDialog v-model="authentication" />
  </TablePageLayout>
</template>
