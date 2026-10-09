<script setup lang="ts">
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocations } from '@/modules/core/common/use-locations';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const emit = defineEmits<{ connect: [location?: string] }>();

/** The exchanges most people start with, offered as shortcuts; any this build cannot connect drop out. */
const POPULAR_EXCHANGES = ['kraken', 'binance', 'coinbase', 'bitstamp', 'kucoin', 'okx'];

const { t } = useI18n({ useScope: 'global' });
const { getExchangeName } = useLocations();
const { exchangesWithKey } = storeToRefs(useLocationStore());

const shortcuts = computed<string[]>(() => POPULAR_EXCHANGES.filter(location => get(exchangesWithKey).includes(location)));
</script>

<template>
  <div
    class="rounded-rui-card border border-rui-divider bg-rui-surface pb-10"
    data-testid="exchange-balances-empty"
  >
    <TableEmptyNotice
      icon="lu-coins-exchange"
      :title="t('exchange_balances.empty.title')"
      :description="t('exchange_balances.empty.description')"
    >
      <RuiButton
        color="primary"
        data-testid="exchange-balances-empty-connect"
        @click="emit('connect')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('exchange_balances.empty.connect') }}
      </RuiButton>
    </TableEmptyNotice>

    <div
      v-if="shortcuts.length > 0"
      class="flex flex-col items-center gap-3 px-4"
    >
      <span class="text-caption uppercase tracking-wide text-rui-text-secondary">
        {{ t('exchange_balances.empty.popular') }}
      </span>
      <div class="flex flex-wrap justify-center gap-2">
        <RuiButton
          v-for="location in shortcuts"
          :key="location"
          variant="outlined"
          data-testid="exchange-balances-empty-shortcut"
          :data-exchange="location"
          @click="emit('connect', location)"
        >
          <template #prepend>
            <LocationIcon
              :item="location"
              icon
              size="18px"
            />
          </template>
          {{ getExchangeName(location) }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
