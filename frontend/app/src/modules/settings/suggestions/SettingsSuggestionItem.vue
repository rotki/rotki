<script setup lang="ts">
import type { PendingSuggestion, SuggestionAction, SuggestionChoice, SuggestionRequirement } from './settings-suggestions';

const { suggestion } = defineProps<{
  suggestion: PendingSuggestion;
  accepted: boolean;
  choice?: string;
}>();

defineEmits<{
  toggle: [];
  select: [choice: string];
  action: [action: SuggestionAction];
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
const choices = computed<SuggestionChoice[]>(() => suggestion.choices ?? []);
const requirements = computed<SuggestionRequirement[]>(() => suggestion.requirements ?? []);

const addedItems = computed<string[]>(() => {
  if (!get(isMerge) || !Array.isArray(suggestion.currentValue) || !Array.isArray(suggestion.suggestedValue))
    return [];
  const current = suggestion.currentValue.map(String);
  return suggestion.suggestedValue.map(String).filter(v => !current.includes(v));
});

function formatValue(value: unknown): string {
  if (typeof value === 'boolean')
    return value ? t('settings_suggestions.dialog.enabled') : t('settings_suggestions.dialog.disabled');
  return String(value);
}

function formatLabel(value: unknown): string {
  return knownLabels[String(value)] ?? String(value);
}

function choiceLabel(item: SuggestionChoice): string {
  return item.id === suggestion.recommendedChoice
    ? t('settings_suggestions.dialog.recommended_choice', { choice: item.label })
    : item.label;
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
        v-if="suggestion.note"
        class="text-caption text-rui-text-secondary mt-1"
      >
        {{ suggestion.note }}
      </div>

      <div
        v-if="requirements.length > 0"
        class="flex flex-wrap gap-x-4 gap-y-1 mt-2"
        data-testid="suggestion-requirements"
      >
        <div
          v-for="requirement in requirements"
          :key="requirement.label"
          class="flex items-center gap-1 text-caption"
          :class="requirement.met ? 'text-rui-success' : 'text-rui-text-secondary'"
        >
          <RuiIcon
            :name="requirement.met ? 'lu-circle-check' : 'lu-circle-x'"
            size="14"
          />
          {{ requirement.label }}
        </div>
      </div>

      <template v-if="choices.length > 0">
        <RuiRadioGroup
          :model-value="choice"
          color="primary"
          hide-details
          class="mt-2"
          data-testid="suggestion-choices"
          @update:model-value="$emit('select', String($event))"
        >
          <RuiRadio
            v-for="item in choices"
            :key="item.id"
            :value="item.id"
            :label="choiceLabel(item)"
            :data-testid="`suggestion-choice-${item.id}`"
          />
        </RuiRadioGroup>

        <RuiButton
          v-if="suggestion.action"
          color="primary"
          variant="outlined"
          size="sm"
          class="mt-2"
          data-testid="suggestion-action"
          @click="$emit('action', suggestion.action)"
        >
          {{ suggestion.action.label }}
        </RuiButton>
      </template>

      <div
        v-else-if="isMerge"
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
