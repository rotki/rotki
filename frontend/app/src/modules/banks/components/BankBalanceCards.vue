<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { RouteLocationRaw } from 'vue-router';
import type { BankBalanceData } from '@/modules/banks/use-bank-data';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { type BankConnectionState, bankConnectionState, bankConnectionStatus, type BankConnectionStatusDisplay } from '@/modules/banks/bank-connection-state';
import BankConnectorIcon from '@/modules/banks/components/BankConnectorIcon.vue';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { banks, selected, total, loading = false } = defineProps<{
  /** The bank connections, in the order to show them. */
  banks: BankBalanceData[];
  /** The connection the page shows, or none for all of them. */
  selected?: string;
  total: BigNumber;
  loading?: boolean;
  isBankLoading: (name: string) => boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

interface BankTile {
  readonly bank: BankBalanceData;
  readonly state: BankConnectionState;
  /** What needs the user, or nothing for a bank that synced fine. */
  readonly status?: BankConnectionStatusDisplay;
}

const tiles = computed<BankTile[]>(() => banks.map((bank) => {
  const state = bankConnectionState(bank);
  return { bank, state, status: bankConnectionStatus(state) };
}));

function linkTo(bank?: string): RouteLocationRaw {
  return { name: '/balances/banks/', query: bank ? { bank } : {} };
}

const tileClass = 'grid grid-cols-[28px_1fr] items-center gap-x-2.5 min-w-0 text-rui-text! rounded-md border px-3 py-2 transition-colors';

function stateClass(active: boolean): string {
  return active
    ? 'border-rui-primary bg-rui-surface'
    : 'border-transparent bg-rui-grey-100 dark:bg-rui-grey-900 hover:border-default hover:bg-white dark:hover:bg-rui-grey-800';
}
</script>

<template>
  <nav
    class="flex gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-[repeat(auto-fill,minmax(220px,1fr))] sm:overflow-visible sm:pb-0"
    :aria-label="t('bank_balances.cards.label')"
    data-testid="bank-balance-cards"
  >
    <RouterLink
      :to="linkTo()"
      :class="[tileClass, stateClass(!selected)]"
      class="shrink-0 w-52 sm:w-auto"
      :aria-current="!selected ? 'page' : undefined"
      data-testid="bank-balance-card"
      data-bank="all"
    >
      <div class="row-span-2 size-7 rounded-full bg-rui-neutral-950/5 dark:bg-white/8 text-rui-text-secondary flex items-center justify-center">
        <RuiIcon
          name="lu-landmark"
          size="16"
        />
      </div>
      <div class="text-xs text-rui-text-secondary truncate">
        {{ t('bank_balances.cards.all') }}
      </div>
      <div class="font-medium truncate">
        <FiatDisplay
          :value="total"
          :loading="loading"
        />
      </div>
    </RouterLink>

    <RouterLink
      v-for="{ bank, state, status } in tiles"
      :key="`${bank.connector}#${bank.name}`"
      :to="linkTo(bank.name)"
      :class="[tileClass, stateClass(selected === bank.name)]"
      class="shrink-0 w-52 sm:w-auto"
      :aria-current="selected === bank.name ? 'page' : undefined"
      data-testid="bank-balance-card"
      :data-bank="bank.name"
    >
      <div class="row-span-3">
        <BankConnectorIcon
          :connector="bank.connector"
          :bank-code="bank.bankCode"
          size="28px"
        />
      </div>
      <div
        class="text-xs text-rui-text-secondary truncate"
        :title="`${bank.name} · ${bank.displayName}`"
      >
        {{ bank.name }}
      </div>
      <div class="flex items-baseline justify-between flex-nowrap gap-x-1.5 min-w-0 font-medium">
        <span class="min-w-0 truncate">
          <FiatDisplay
            :value="bank.total"
            :loading="isBankLoading(bank.name)"
          />
        </span>
        <PercentageDisplay
          class="shrink-0 text-xs font-normal text-rui-text-secondary"
          :value="calculatePercentage(bank.total, total)"
        />
      </div>
      <div
        v-if="status"
        class="flex items-center gap-1 text-xs min-w-0"
        :class="status.textClass"
        data-testid="bank-balance-card-status"
        :data-state="state"
      >
        <RuiIcon
          :name="status.icon"
          size="12"
          class="shrink-0"
        />
        <span class="truncate">{{ t(status.short) }}</span>
      </div>
      <i18n-t
        v-else-if="bank.syncStatus.lastSyncTs"
        scope="global"
        keypath="bank_balances.cards.synced"
        tag="div"
        class="text-xs text-rui-text-secondary truncate"
        data-testid="bank-balance-card-status"
      >
        <template #connector>
          {{ bank.displayName }}
        </template>
        <template #time>
          <TimeAgoDisplay :timestamp="bank.syncStatus.lastSyncTs" />
        </template>
      </i18n-t>
      <div
        v-else
        class="text-xs text-rui-text-secondary truncate"
        data-testid="bank-balance-card-status"
      >
        {{ bank.displayName }}
      </div>
    </RouterLink>
  </nav>
</template>
