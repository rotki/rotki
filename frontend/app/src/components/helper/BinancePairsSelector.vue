<template>
  <v-autocomplete
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
      <v-chip
        v-bind="data.attrs"
        :input-value="data.selected"
        :click="data.select"
        filter
        close
        @click:close="data.parent.selectItem(data.item)"
      >
        {{ data.item }}
      </v-chip>
    </template>
    <template #item="data">
      <div
        class="binance-market-selector__list__item d-flex justify-space-between flex-grow-1"
      >
        <div class="binance-market-selector__list__item__address-label">
          <v-chip :color="dark ? null : 'grey lighten-3'" filter>
            {{ data.item }}
          </v-chip>
        </div>
      </div>
    </template>
  </v-autocomplete>
</template>

<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { useTheme } from '@/composables/common';
import { useExchangeApi } from '@/services/balances/exchanges';
import { useNotifications } from '@/store/notifications';
import { uniqueStrings } from '@/utils/data';

const props = defineProps({
  label: { required: false, type: String, default: '' },
  outlined: { required: false, type: Boolean, default: false },
  name: { required: true, type: String },
  location: { required: true, type: String }
});

const emit = defineEmits(['input']);
const { name, location } = toRefs(props);
const { dark } = useTheme();

const input = (_value: string[]) => emit('input', _value);

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
    const { notify } = useNotifications();
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
    const { notify } = useNotifications();
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

  return pair.indexOf(query) > -1;
};

watch(search, search => {
  if (search) {
    const pairs = search.split(' ');
    if (pairs.length > 0) {
      const useLastPairs = search.substr(search.length - 1) === ' ';
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

<style scoped lang="scss">
.binance-market-selector {
  &--outlined {
    :deep() {
      /* stylelint-disable */
      .v-label:not(.v-label--active) {
        /* stylelint-enable */
        top: 24px;
      }

      .v-input {
        &__icon {
          &--clear {
            margin-top: 6px;
          }

          &--append {
            margin-top: 6px;
          }
        }
      }
    }
  }
}
</style>
