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
    outlined: false
  }
);

const emit = defineEmits<{ (e: 'input', pairs: string[]): void }>();
const { name, location } = toRefs(props);

const input = (value: string[]) => emit('input', value);

const search = ref<string>('');
const queriedMarkets = ref<string[]>([]);
const selection = ref<string[]>([]);
const allMarkets = ref<string[]>([]);
const loading = ref<boolean>(false);

const handleInput = (value: string[]) => {
  set(selection, value);
  input(value);
};

const { t } = useI18n();
const api = useExchangeApi();

const { notify } = useNotificationsStore();

onMounted(async () => {
  set(loading, true);
  try {
    set(
      queriedMarkets,
      await api.queryBinanceUserMarkets(get(name), get(location))
    );
  } catch (e: any) {
    const title = t('binance_market_selector.query_user.title').toString();
    const description = t('binance_market_selector.query_user.error', {
      message: e.message
    }).toString();
    notify({
      title,
      message: description,
      severity: Severity.ERROR,
      display: true
    });
  }

  try {
    set(allMarkets, await api.queryBinanceMarkets(get(location)));
  } catch (e: any) {
    const title = t('binance_market_selector.query_all.title').toString();
    const description = t('binance_market_selector.query_all.error', {
      message: e.message
    }).toString();
    notify({
      title,
      message: description,
      severity: Severity.ERROR,
      display: true
    });
  }

  set(loading, false);
  set(selection, get(queriedMarkets));
});

const filter = (item: string, queryText: string) => {
  const query = queryText.toLocaleLowerCase();
  const pair = item.toLocaleLowerCase();

  return pair.includes(query);
};

watch(search, search => {
  if (search) {
    const pairs = search.split(' ');
    if (pairs.length > 0) {
      const useLastPairs = search.slice(-1) === ' ';
      if (useLastPairs) {
        search = '';
      } else {
        search = pairs.pop()!;
      }
      const matchedPairs = pairs.filter(pair => get(allMarkets).includes(pair));
      handleInput([...get(selection), ...matchedPairs].filter(uniqueStrings));
    }
  }
});
</script>

<template>
  <VAutocomplete
    v-bind="$attrs"
    :items="allMarkets"
    :filter="filter"
    :search-input.sync="search"
    multiple
    :loading="loading"
    :disabled="loading"
    hide-details
    hide-selected
    hide-no-data
    return-object
    chips
    clearable
    :outlined="outlined"
    :open-on-clear="false"
    :label="label ? label : t('binance_market_selector.default_label')"
    :class="outlined ? 'binance-market-selector--outlined' : null"
    item-text="address"
    item-value="address"
    class="binance-market-selector"
    :value="selection"
    @input="handleInput($event)"
    @change="search = ''"
  >
    <template #selection="data">
      <RuiChip
        class="m-0.5"
        size="sm"
        v-bind="data.attrs"
        :click="data.select"
        closeable
        @click:close="data.parent.selectItem(data.item)"
      >
        {{ data.item }}
      </RuiChip>
    </template>
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
  </VAutocomplete>
</template>

<style scoped lang="scss">
.binance-market-selector {
  &--outlined {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.v-label) {
      &:not(.v-label--active) {
        top: 24px;
      }
    }

    :deep(.v-input__icon) {
      margin-top: 6px;
    }
    /* stylelint-enable selector-class-pattern,selector-nested-pattern */
  }
}
</style>
