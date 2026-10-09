<script setup lang="ts">
import ExchangeRefreshMenuItem from '@/modules/balances/exchanges/ExchangeRefreshMenuItem.vue';
import { useLocations } from '@/modules/core/common/use-locations';

const { exchanges, selected, loading = false } = defineProps<{
  exchanges: string[];
  /** The exchange the page shows; the button then refreshes only it. */
  selected?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'refresh-all': [];
  'refresh-exchange': [exchange: string];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getExchangeName } = useLocations();

const menuOpen = ref<boolean>(false);

const tooltip = computed<string>(() => selected
  ? t('exchange_balances.refresh_menu.exchange', { exchange: getExchangeName(selected) })
  : t('exchange_balances.refresh_menu.all'));

function refreshAll(): void {
  set(menuOpen, false);
  emit('refresh-all');
}

function refreshExchange(exchange: string): void {
  set(menuOpen, false);
  emit('refresh-exchange', exchange);
}
</script>

<template>
  <!--
    The button refreshes what the page shows: every exchange, or the one selected. The menu reaches
    any single exchange, or all of them, from wherever the page is.
  -->
  <RuiButtonGroup
    variant="outlined"
    color="primary"
  >
    <RuiTooltip
      :open-delay="400"
      :class-names="{ root: 'flex' }"
    >
      <template #activator>
        <RuiButton
          data-testid="refresh-exchange-balances"
          :disabled="exchanges.length === 0"
          :loading="loading"
          @click="emit('refresh')"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
      </template>
      {{ tooltip }}
    </RuiTooltip>
    <RuiMenu
      v-model="menuOpen"
      :options="{ placement: 'bottom-end' }"
      :class-names="{ root: 'flex' }"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="{
            ...attrs,
            'data-testid': 'refresh-exchange-balances-menu',
          }"
          color="primary"
          variant="outlined"
          class="outline-0! px-2"
          :disabled="exchanges.length === 0"
          :aria-label="t('exchange_balances.refresh_menu.title')"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <div class="w-72 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="loading"
          data-testid="refresh-exchange-menu-all"
          @click="refreshAll()"
        >
          <template #prepend>
            <RuiIcon
              size="18"
              name="lu-refresh-ccw"
            />
          </template>
          {{ t('exchange_balances.refresh_menu.all') }}
        </RuiButton>
        <RuiDivider class="my-1" />
        <div class="px-4 pt-1 pb-1 text-caption uppercase tracking-wide text-rui-text-secondary">
          {{ t('exchange_balances.refresh_menu.section') }}
        </div>
        <ExchangeRefreshMenuItem
          v-for="exchange in exchanges"
          :key="exchange"
          :exchange="exchange"
          @refresh="refreshExchange($event)"
        />
      </div>
    </RuiMenu>
  </RuiButtonGroup>
</template>
