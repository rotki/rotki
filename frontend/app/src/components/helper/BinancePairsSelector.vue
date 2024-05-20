<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';

const props = withDefaults(
  defineProps<{
    label?: string;
    outlined?: boolean;
    name: string;
    location: string;
  }>(),
  {
    label: '',
    outlined: false,
  },
);

const emit = defineEmits<{ (e: 'input', pairs: string[]): void }>();
const { name, location } = toRefs(props);

const input = (value: string[]) => emit('input', value);

const queriedMarkets = ref<string[]>([]);
const selection = ref<string[]>([]);
const allMarkets = ref<string[]>([]);
const loading = ref<boolean>(false);

function handleInput(value: string[]) {
  set(selection, value);
  input(value);
}

const { t } = useI18n();
const api = useExchangeApi();

const { notify } = useNotificationsStore();

onMounted(async () => {
  set(loading, true);
  try {
    set(
      queriedMarkets,
      await api.queryBinanceUserMarkets(get(name), get(location)),
    );
  }
  catch (error: any) {
    const title = t('binance_market_selector.query_user.title');
    const description = t('binance_market_selector.query_user.error', {
      message: error.message,
    });
    notify({
      title,
      message: description,
      severity: Severity.ERROR,
      display: true,
    });
  }

  try {
    set(allMarkets, await api.queryBinanceMarkets(get(location)));
  }
  catch (error: any) {
    const title = t('binance_market_selector.query_all.title');
    const description = t('binance_market_selector.query_all.error', {
      message: error.message,
    });
    notify({
      title,
      message: description,
      severity: Severity.ERROR,
      display: true,
    });
  }

  set(loading, false);
  set(selection, get(queriedMarkets));
});
</script>

<template>
  <RuiAutoComplete
    v-bind="$attrs"
    :options="allMarkets"
    :loading="loading"
    :disabled="loading"
    hide-details
    hide-selected
    chips
    clearable
    variant="outlined"
    :label="label || t('binance_market_selector.default_label')"
    class="binance-market-selector"
    :value="selection"
    :item-height="54"
    @input="handleInput($event)"
  >
    <template #item="data">
      <div
        class="binance-market-selector__list__item flex justify-between grow"
      >
        <div class="binance-market-selector__list__item__address-label">
          <RuiChip size="sm">
            {{ data.item }}
          </RuiChip>
        </div>
      </div>
    </template>
  </RuiAutoComplete>
</template>
