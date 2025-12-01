<script setup lang="ts">
import { Severity } from '@rotki/common';
import { backoff } from '@shared/utils';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useNotificationsStore } from '@/store/notifications';
import { trimOnPaste } from '@/utils/event';

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

interface PasteResult {
  valid: string[];
  invalid: string[];
}

const pasteResult = ref<PasteResult>();

function onPaste(event: ClipboardEvent): void {
  const paste = trimOnPaste(event);
  if (!paste)
    return;

  const markets = get(allMarkets);
  if (markets.length === 0)
    return;

  const marketsSet = new Set(markets);
  const currentSelection = new Set(get(selection));

  // Split by comma, newline, or space
  const pastedPairs = paste
    .split(/[\s,]+/)
    .map(pair => pair.trim())
    .filter(pair => pair.length > 0);

  const validPairs: string[] = [];
  const invalidPairs: string[] = [];

  for (const pair of pastedPairs) {
    if (marketsSet.has(pair)) {
      validPairs.push(pair);
      if (!currentSelection.has(pair)) {
        currentSelection.add(pair);
      }
    }
    else {
      invalidPairs.push(pair);
    }
  }

  // Update selection with new pairs (duplicates are handled by Set)
  const newSelection = [...currentSelection];
  set(selection, newSelection);
  updateSelection(newSelection);

  set(pasteResult, {
    invalid: invalidPairs,
    valid: validPairs,
  });
}

function dismissPasteResult(): void {
  set(pasteResult, undefined);
}

function onSelectionChange(value: string[]) {
  dismissPasteResult();
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
  <div class="flex flex-col gap-2">
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
        @paste="onPaste($event)"
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
    <RuiAlert
      v-if="pasteResult"
      :type="pasteResult.invalid.length > 0 ? 'warning' : 'success'"
      closeable
      @close="dismissPasteResult()"
    >
      <div class="flex flex-col gap-1">
        <span v-if="pasteResult.valid.length > 0">
          {{ t('binance_market_selector.paste_result.valid', { count: pasteResult.valid.length }, pasteResult.valid.length) }}
        </span>
        <div v-if="pasteResult.invalid.length > 0">
          <div>
            {{ t('binance_market_selector.paste_result.invalid', { count: pasteResult.invalid.length }, pasteResult.invalid.length) }}
          </div>
          <div class="text-rui-text-secondary text-sm mt-1">
            {{ pasteResult.invalid.join(', ') }}
          </div>
        </div>
      </div>
    </RuiAlert>
  </div>
</template>
