<script setup lang="ts">
import type { PendingSuggestion } from './settings-suggestions';

const { suggestion } = defineProps<{
  suggestion: PendingSuggestion;
  accepted: boolean;
}>();

defineEmits<{
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const knownLabels: Record<string, string> = {
  base: 'Base',
  coingecko: 'CoinGecko',
  cryptocompare: 'CryptoCompare',
  defillama: 'DefiLlama',
  gnosis: 'Gnosis',
  polygon_pos: 'Polygon PoS',
  uniswapv2: 'Uniswap v2',
  uniswapv3: 'Uniswap v3',
};

const isArray = computed<boolean>(() => Array.isArray(suggestion.currentValue));
const isMerge = computed<boolean>(() => !!suggestion.merge);

const addedItems = computed<string[]>(() => {
  if (!get(isMerge) || !Array.isArray(suggestion.currentValue) || !Array.isArray(suggestion.suggestedValue))
    return [];
  const current = suggestion.currentValue as string[];
  return (suggestion.suggestedValue as string[]).filter(v => !current.includes(v));
});

function formatValue(value: unknown): string {
  if (typeof value === 'boolean')
    return value ? t('settings_suggestions.dialog.enabled') : t('settings_suggestions.dialog.disabled');
  return String(value);
}

function formatLabel(value: unknown): string {
  return knownLabels[String(value)] ?? String(value);
}
</script>

<template>
  <div class="flex items-start gap-3 py-2 border-b border-default last:border-b-0">
    <RuiCheckbox
      :model-value="accepted"
      hide-details
      class="mt-0.5"
      @update:model-value="$emit('toggle')"
    />
    <div class="flex-1 min-w-0">
      <div class="text-body-1">
        {{ suggestion.description }}
      </div>

      <div
        v-if="isMerge"
        class="text-caption text-rui-text-secondary mt-0.5"
      >
        {{ t("settings_suggestions.dialog.adding") }}
        <span class="font-bold text-rui-text">
          {{ addedItems.map(v => formatLabel(v)).join(', ') }}
        </span>
      </div>

      <div
        v-else-if="!isArray"
        class="text-caption text-rui-text-secondary mt-0.5"
      >
        {{ formatValue(suggestion.currentValue) }}
        <RuiIcon
          name="lu-arrow-right"
          class="inline-block mx-1 text-rui-primary"
          size="12"
        />
        <span class="font-bold text-rui-text">
          {{ formatValue(suggestion.suggestedValue) }}
        </span>
      </div>

      <div
        v-else
        class="grid grid-cols-[1fr_auto_1fr] gap-x-3 mt-1.5"
      >
        <ol class="text-caption text-rui-text-secondary list-decimal list-inside space-y-0.5">
          <li
            v-for="(val, i) in (suggestion.currentValue as unknown[])"
            :key="i"
          >
            {{ formatLabel(val) }}
          </li>
        </ol>

        <div class="flex items-center">
          <RuiIcon
            name="lu-arrow-right"
            class="text-rui-primary"
            size="14"
          />
        </div>

        <ol class="text-caption font-bold text-rui-text list-decimal list-inside space-y-0.5">
          <li
            v-for="(val, i) in (suggestion.suggestedValue as unknown[])"
            :key="i"
          >
            {{ formatLabel(val) }}
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>
