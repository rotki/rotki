<script setup lang="ts">
import { Severity } from '@rotki/common';
import { backoff } from '@shared/utils';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useNotificationsStore } from '@/store/notifications';

defineOptions({
  inheritAttrs: false,
});

const props = defineProps<{
  name: string;
  edit: boolean;
  location: string;
  errorMessages?: string[];
}>();

const emit = defineEmits<{
  (e: 'update:selection', pairs: string[]): void;
}>();

const MAX_RETRIES = 3;

const { edit, errorMessages, location, name } = toRefs(props);

const updateSelection = (value: string[]) => emit('update:selection', value);

const queriedMarkets = ref<string[]>([]);
const selection = ref<string[]>([]);
const allMarkets = ref<string[]>([]);
const loading = ref<boolean>(false);

function onSelectionChange(value: string[]) {
  set(selection, value);
  updateSelection(value);
}

const { t } = useI18n({ useScope: 'global' });
const api = useExchangeApi();

const { notify } = useNotificationsStore();

async function queryAllMarkets() {
  try {
    const markets = await backoff(
      MAX_RETRIES,
      () => api.queryBinanceMarkets(get(location)),
      1000, // Initial delay of 1 second
    );
    set(allMarkets, markets);
  }
  catch (error: any) {
    const title = t('binance_market_selector.query_all.title');
    const description = t('binance_market_selector.query_all.error', {
      message: error.message,
    });
    notify({
      display: true,
      message: description,
      severity: Severity.ERROR,
      title,
    });
  }
}

async function loadUserMarkets() {
  if (get(edit)) {
    try {
      const markets = await api.queryBinanceUserMarkets(get(name), get(location));
      set(queriedMarkets, markets);
      set(selection, markets);
    }
    catch (error: any) {
      const title = t('binance_market_selector.query_user.title');
      const description = t('binance_market_selector.query_user.error', {
        message: error.message,
      });
      notify({
        display: true,
        message: description,
        severity: Severity.ERROR,
        title,
      });
    }
  }
}

async function refreshMarkets(refreshUserMarkets = false) {
  set(loading, true);
  if (refreshUserMarkets) {
    await loadUserMarkets();
  }
  await queryAllMarkets();
  set(loading, false);
}

onMounted(() => {
  refreshMarkets(true);
});
</script>

<template>
  <div class="flex items-start gap-2">
    <RuiAutoComplete
      v-bind="$attrs"
      :options="allMarkets"
      :loading="loading"
      :disabled="loading"
      :error-messages="errorMessages"
      hide-selected
      chips
      clearable
      auto-select-first
      variant="outlined"
      :label="t('binance_market_selector.default_label')"
      class="binance-market-selector"
      :model-value="selection"
      :item-height="54"
      @update:model-value="onSelectionChange($event)"
    >
      <template #item="data">
        <div class="binance-market-selector__list__item flex justify-between grow">
          <div class="binance-market-selector__list__item__address-label">
            <RuiChip size="sm">
              {{ data.item }}
            </RuiChip>
          </div>
        </div>
      </template>
    </RuiAutoComplete>
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          class="mt-1"
          variant="text"
          icon
          color="primary"
          :loading="loading"
          :disabled="loading"
          @click="refreshMarkets()"
        >
          <RuiIcon name="lu-refresh-ccw" />
        </RuiButton>
      </template>
      {{ t('binance_market_selector.refresh_tooltip') }}
    </RuiTooltip>
  </div>
</template>
