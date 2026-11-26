<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { storeToRefs } from 'pinia';
import { computed, onBeforeMount, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import BankBalanceCards from '@/modules/banks/components/BankBalanceCards.vue';
import BankBalancesEmpty from '@/modules/banks/components/BankBalancesEmpty.vue';
import BankBalancesPageButtons from '@/modules/banks/components/BankBalancesPageButtons.vue';
import BankBalancesTableBody from '@/modules/banks/components/BankBalancesTableBody.vue';
import BankConnectionItem from '@/modules/banks/components/BankConnectionItem.vue';
import BankConnectionsFailure from '@/modules/banks/components/BankConnectionsFailure.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import TableSearchField from '@/modules/core/table/TableSearchField.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useBankBalancesPage } from '@/pages/balances/banks/use-bank-balances-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.bank_balances'), icon: 'lu-landmark', parent: '/balances/', order: 25, drawer: 'balances-banks' },
  },
});

const { t } = useI18n({ useScope: 'global' });
const route = useRoute();
const router = useRouter();

const search = ref<string>('');

const { canAddBank, connections, connectionsError } = storeToRefs(useBankConnectionsStore());
const { refreshBankConnections, refreshSupportedBanks, syncBanks, fetchBankBalances } = useBanks();

/** The stable identifier of the connection selected in the route. */
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

async function load(ignoreCache = false): Promise<void> {
  await refreshBankConnections();
  await fetchBankBalances(ignoreCache);
}

async function connect(connector?: string): Promise<void> {
  await router.push({ name: '/accounts/banks/', query: { add: 'true', ...(connector ? { connector } : {}) } });
}

onBeforeMount(() => {
  startPromise(refreshSupportedBanks());
  startPromise(load());
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.bank_balances')]">
    <template #buttons>
      <BankBalancesPageButtons
        :banks="banks"
        :selected="selectedBank?.identifier"
        :loading="loading"
        :is-bank-loading="isBankLoading"
        :connected="connections.length > 0"
        :can-add="canAddBank"
        @refresh="startPromise(refreshInView())"
        @refresh-all="startPromise(refreshAll())"
        @refresh-bank="startPromise(refreshBank($event))"
        @add="connect()"
      />
    </template>

    <BankConnectionsFailure
      v-if="connectionsError"
      :failure="connectionsError"
      :blocking="connections.length === 0"
      @retry="load(true)"
    />

    <BankBalancesEmpty
      v-if="connections.length === 0 && !connectionsError"
      @connect="connect($event)"
    />

    <template v-else-if="connections.length > 0">
      <BankBalanceCards
        :banks="banks"
        :selected="selectedBank?.identifier"
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
              :key="connection.identifier"
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

        <BankBalancesTableBody
          v-model:search="search"
          :selected-bank="selectedBank"
          :balances="balances"
          :loading="loading"
          :is-bank-loading="isBankLoading"
        />
      </TableFrame>
    </template>
  </TablePageLayout>
</template>
