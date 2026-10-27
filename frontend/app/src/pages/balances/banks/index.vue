<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import BankBalancesEmpty from '@/modules/banks/components/BankBalancesEmpty.vue';
import BankConnectionItem from '@/modules/banks/components/BankConnectionItem.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankData } from '@/modules/banks/use-bank-data';
import { useBanks } from '@/modules/banks/use-banks';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import TableSearchField from '@/modules/core/table/TableSearchField.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.bank_balances'), icon: 'lu-landmark', parent: '/balances/', order: 25, drawer: 'balances-banks' },
  },
});

const search = ref<string>('');

const { connections, connectionsError } = storeToRefs(useBankConnectionsStore());
const { balances, banks } = useBankData();
const { fetchBankBalances, refreshBankConnections, refreshSupportedBanks, syncBanks } = useBanks();
const { useIsActive } = useTaskCenter();
const failureMessage = useFailureMessage();
const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const loading = useIsActive(ActivityKind.BANK_BALANCES);

async function refresh(ignoreCache = false): Promise<void> {
  await refreshBankConnections();
  await fetchBankBalances(ignoreCache);
}

async function connect(location?: string): Promise<void> {
  await router.push({ path: '/api-keys/banks', query: { add: 'true', ...(location ? { location } : {}) } });
}

onBeforeMount(() => {
  startPromise(refreshSupportedBanks());
  startPromise(refresh());
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.balances'), t('navigation_menu.balances_sub.bank_balances')]">
    <template #buttons>
      <RuiTooltip
        v-if="connections.length > 0"
        :open-delay="400"
      >
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
          @retry="refresh()"
        />
      </TableEmptyNotice>
    </div>
    <FailureStrip
      v-else-if="connectionsError"
      class="mb-4"
      :title="t('bank_balances.connections_failed')"
      :message="failureMessage(connectionsError)"
      data-testid="bank-connections-error"
      @retry="refresh()"
    />

    <BankBalancesEmpty
      v-if="connections.length === 0 && !connectionsError"
      @connect="connect($event)"
    />

    <TableFrame
      v-else-if="connections.length > 0"
      data-testid="bank-balances"
    >
      <template #toolbar>
        <ul
          class="flex flex-col gap-1 min-w-0 p-0 m-0 list-none"
          :aria-label="t('bank_balances.connections')"
        >
          <BankConnectionItem
            v-for="connection in connections"
            :key="`${connection.location}#${connection.name}`"
            :connection="connection"
            @sync="startPromise(syncBanks($event))"
          />
        </ul>
        <TableSearchField
          v-model="search"
          data-testid="bank-balances-search"
        />
      </template>

      <AssetBalances
        v-model:search="search"
        data-testid="bank-asset-balances"
        :breakdown="{ hide: true }"
        :loading="loading && balances.length === 0"
        :balances="balances"
        :show-per-protocol="banks.length > 1"
        sticky-header
      >
        <template #empty>
          <TableEmptyNotice
            icon="lu-landmark"
            :title="t('bank_balances.empty_table.title')"
            :description="t('bank_balances.empty_table.description')"
          />
        </template>
      </AssetBalances>
    </TableFrame>
  </TablePageLayout>
</template>
