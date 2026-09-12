<script setup lang="ts">
import { type AssetBalanceWithPrice, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankData } from '@/modules/banks/use-bank-data';
import { useBanks } from '@/modules/banks/use-banks';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.bank_balances'), icon: 'lu-landmark', parent: '/balances/', order: 25, drawer: 'balances-banks' },
  },
});

interface BankLocationBalances {
  location: string;
  balances: AssetBalanceWithPrice[];
}

const { connections } = storeToRefs(useBankConnectionsStore());
const { banks } = useBankData();
const { fetchBankBalances, refreshBankConnections } = useBanks();
const { useIsActive } = useTaskCenter();
const { t } = useI18n({ useScope: 'global' });

const loading = useIsActive(ActivityKind.BANK_BALANCES);

/** The backend already prices each balance in the main currency, so the price is implied. */
const perLocation = computed<BankLocationBalances[]>(() => get(banks).map(bank => ({
  balances: Object.entries(bank.balances).map(([asset, { amount, value }]) => ({
    amount,
    asset,
    price: amount.isZero() ? Zero : value.div(amount),
    value,
  })),
  location: bank.location,
})));

async function refresh(ignoreCache = false): Promise<void> {
  await refreshBankConnections();
  await fetchBankBalances(ignoreCache);
}

onBeforeMount(() => {
  startPromise(refresh());
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.bank_balances')]">
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            data-testid="refresh-bank-balances"
            @click="refresh(true)"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-cw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('bank_balances.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        data-testid="add-bank-connection"
        :to="{ path: '/api-keys/banks', query: { add: 'true' } }"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('bank_balances.add_bank') }}
      </RuiButton>
    </template>

    <RuiCard
      v-for="entry in perLocation"
      :key="entry.location"
      data-testid="bank-balances-card"
    >
      <template #header>
        <LocationDisplay
          :identifier="entry.location"
          :open-details="false"
        />
      </template>
      <AssetBalances
        :balances="entry.balances"
        :loading="loading"
      />
    </RuiCard>

    <RuiCard v-if="perLocation.length === 0">
      <div
        class="p-4 text-rui-text-secondary"
        data-testid="bank-balances-empty"
      >
        <template v-if="connections.length === 0">
          <i18n-t
            scope="global"
            keypath="bank_balances.no_connections"
            tag="span"
          >
            <InternalLink :to="{ path: '/api-keys/banks', query: { add: 'true' } }">
              {{ t('bank_balances.click_here') }}
            </InternalLink>
          </i18n-t>
        </template>
        <template v-else>
          {{ t('bank_balances.no_balances') }}
        </template>
      </div>
    </RuiCard>
  </TablePageLayout>
</template>
