<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { RouteLocationRaw } from 'vue-router';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import { useLocations } from '@/modules/core/common/use-locations';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';

const { exchanges, selected, total } = defineProps<{
  /** The connected exchanges, in the order to show them. */
  exchanges: string[];
  /** The exchange the page shows, or none for all of them. */
  selected?: string;
  total: BigNumber;
  exchangeBalance: (exchange: string) => BigNumber;
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getExchangeName } = useLocations();

function linkTo(exchange?: string): RouteLocationRaw {
  return { name: '/balances/exchange/[[exchange]]', params: exchange ? { exchange } : {} };
}

const tileClass = 'grid grid-cols-[28px_1fr] items-center gap-x-2.5 min-w-0 text-rui-text! rounded-md border px-3 py-2 transition-colors';

function stateClass(active: boolean): string {
  return active
    ? 'border-rui-primary bg-rui-surface'
    : 'border-transparent bg-rui-grey-100 dark:bg-rui-grey-900 hover:border-default hover:bg-white dark:hover:bg-rui-grey-800';
}
</script>

<template>
  <!--
    The page's navigation: all exchanges together, then each one with its share. A row that scrolls
    sideways on a narrow screen rather than wrapping into a wall of tiles.
  -->
  <nav
    class="flex gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-[repeat(auto-fill,minmax(200px,1fr))] sm:overflow-visible sm:pb-0"
    :aria-label="t('exchange_balances.cards.label')"
    data-testid="exchange-balance-cards"
  >
    <RouterLink
      :to="linkTo()"
      :class="[tileClass, stateClass(!selected)]"
      class="shrink-0 w-48 sm:w-auto"
      :aria-current="!selected ? 'page' : undefined"
      data-testid="exchange-balance-card"
      data-exchange="all"
    >
      <div class="row-span-2 size-7 rounded-full bg-rui-neutral-950/5 dark:bg-white/8 text-rui-text-secondary flex items-center justify-center">
        <RuiIcon
          name="lu-coins-exchange"
          size="16"
        />
      </div>
      <div class="text-xs text-rui-text-secondary truncate">
        {{ t('exchange_balances.cards.all') }}
      </div>
      <div class="font-medium truncate">
        <FiatDisplay
          :value="total"
          :loading="loading"
        />
      </div>
    </RouterLink>

    <RouterLink
      v-for="exchange in exchanges"
      :key="exchange"
      :to="linkTo(exchange)"
      :class="[tileClass, stateClass(selected === exchange)]"
      class="shrink-0 w-48 sm:w-auto"
      :aria-current="selected === exchange ? 'page' : undefined"
      data-testid="exchange-balance-card"
      :data-exchange="exchange"
    >
      <div class="row-span-2">
        <LocationIcon
          :item="exchange"
          icon
          size="28px"
        />
      </div>
      <div class="text-xs text-rui-text-secondary truncate">
        {{ getExchangeName(exchange) }}
      </div>
      <div class="flex items-baseline justify-between flex-nowrap gap-x-1.5 min-w-0 font-medium">
        <span class="min-w-0 truncate">
          <FiatDisplay
            :value="exchangeBalance(exchange)"
            :loading="loading"
          />
        </span>
        <PercentageDisplay
          class="shrink-0 text-xs font-normal text-rui-text-secondary"
          :value="calculatePercentage(exchangeBalance(exchange), total)"
        />
      </div>
    </RouterLink>
  </nav>
</template>
