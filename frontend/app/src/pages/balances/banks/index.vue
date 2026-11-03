<script setup lang="ts">
import type { FormatOptions } from '@/modules/assets/amount-display/types';
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import BankBalanceCards from '@/modules/banks/components/BankBalanceCards.vue';
import BankBalancesEmpty from '@/modules/banks/components/BankBalancesEmpty.vue';
import BankBalancesRefreshButton from '@/modules/banks/components/BankBalancesRefreshButton.vue';
import BankConnectionItem from '@/modules/banks/components/BankConnectionItem.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import TableSearchField from '@/modules/core/table/TableSearchField.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useBankBalancesPage } from '@/pages/balances/banks/use-bank-balances-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.bank_balances'), icon: 'lu-landmark', parent: '/balances/', order: 25, drawer: 'balances-banks' },
  },
});

/** Bank balances are kept in cents, so every amount shows exactly two decimals. */
const BANK_AMOUNT_FORMAT: FormatOptions = { decimals: 2 };

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();
const router = useRouter();

const search = ref<string>('');

const { connections, connectionsError } = storeToRefs(useBankConnectionsStore());
const { refreshBankConnections, refreshSupportedBanks, syncBanks, fetchBankBalances } = useBanks();
const failureMessage = useFailureMessage();

/** The connection named in the route; names are unique across banks. */
const selected = computed<string | undefined>(() => {
  const bank = route.query.bank;
  return typeof bank === 'string' && bank !== '' ? bank : undefined;
});

const {
  balances,
  banks,
  isBankLoading,
  issues,
  loading,
  refreshAll,
  refreshBank,
  refreshInView,
  selectedBank,
  total,
} = useBankBalancesPage(selected);

async function load(): Promise<void> {
  await refreshBankConnections();
  await fetchBankBalances();
}

async function connect(connector?: string): Promise<void> {
  await router.push({ path: '/api-keys/banks', query: { add: 'true', ...(connector ? { connector } : {}) } });
}

onBeforeMount(() => {
  startPromise(refreshSupportedBanks());
  startPromise(load());
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.bank_balances')]">
    <template #buttons>
      <BankBalancesRefreshButton
        v-if="connections.length > 0"
        :banks="banks"
        :selected="selectedBank?.name"
        :loading="loading"
        @refresh="startPromise(refreshInView())"
        @refresh-all="startPromise(refreshAll())"
        @refresh-bank="startPromise(refreshBank($event))"
      />
      <RuiButton
        color="primary"
        data-testid="add-bank-connection"
        @click="connect()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('bank_balances.add_bank') }}
      </RuiButton>
    </template>

    <div
      v-if="connectionsError && connections.length === 0"
      class="rounded-rui-card border border-rui-divider bg-rui-surface"
      data-testid="bank-connections-error"
    >
      <TableEmptyNotice
        icon="lu-landmark"
        :title="t('bank_balances.connections_failed')"
      >
        <TableFailureDescription
          :message="failureMessage(connectionsError)"
          @retry="load()"
        />
      </TableEmptyNotice>
    </div>
    <FailureStrip
      v-else-if="connectionsError"
      class="mb-4"
      :title="t('bank_balances.connections_failed')"
      :failure="connectionsError"
      data-testid="bank-connections-error"
      @retry="load()"
    />

    <BankBalancesEmpty
      v-if="connections.length === 0 && !connectionsError"
      @connect="connect($event)"
    />

    <template v-else-if="connections.length > 0">
      <BankBalanceCards
        :banks="banks"
        :selected="selectedBank?.name"
        :total="total"
        :loading="loading"
        :is-bank-loading="isBankLoading"
      />

      <TableFrame data-testid="bank-balances">
        <template #toolbar>
          <ul
            v-if="issues.length > 0"
            class="flex flex-col gap-1 min-w-0 p-0 m-0 list-none"
            :aria-label="t('bank_balances.connections')"
            data-testid="bank-balances-issues"
          >
            <BankConnectionItem
              v-for="connection in issues"
              :key="`${connection.connector}#${connection.name}`"
              :connection="connection"
              @sync="startPromise(syncBanks($event))"
            />
          </ul>
          <TableSearchField
            v-model="search"
            class="ml-auto"
            data-testid="bank-balances-search"
          />
        </template>

        <AssetBalances
          v-if="balances.length > 0 || loading"
          v-model:search="search"
          data-testid="bank-asset-balances"
          :breakdown="{ hide: true }"
          :loading="loading && balances.length === 0"
          :balances="balances"
          sticky-header
        >
          <template #amount="{ row }">
            <ValueDisplay
              :value="row.amount"
              :format="BANK_AMOUNT_FORMAT"
            />
          </template>
        </AssetBalances>
        <TableEmptyNotice
          v-else
          icon="lu-landmark"
          :title="t('bank_balances.empty_table.title')"
          :description="t('bank_balances.empty_table.description')"
        />
      </TableFrame>
    </template>
  </TablePageLayout>
</template>
