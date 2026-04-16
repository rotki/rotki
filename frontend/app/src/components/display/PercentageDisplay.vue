<script setup lang="ts">
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const { assetPadding = 0, justify = 'end', value } = defineProps<{
  value?: string;
  justify?: 'end' | 'start';
  assetPadding?: number;
}>();

const { shouldShowPercentage } = storeToRefs(useFrontendSettingsStore());

const displayValue = computed<string>(() => {
  if (!get(shouldShowPercentage))
    return (Math.random() * 100 + 1).toFixed(2);

  if (value === undefined)
    return '-';

  return value.replace('%', '');
});

const assetStyle = computed<Record<string, string | undefined>>(() => {
  if (!assetPadding) {
    return {
      'max-width': '0ch',
    };
  }
  return {
    'text-align': 'start',
    'width': `${assetPadding + 1}ch`,
  };
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="flex percentage-display items-baseline gap-1 flex-nowrap"
    :class="{
      'justify-start': justify === 'start',
      'justify-end': justify === 'end',
    }"
  >
    <div
      data-cy="percentage-display"
      :class="{
        'blur': !shouldShowPercentage,
        'text-end': justify === 'end',
        'text-start': justify === 'start',
      }"
    >
      {{ displayValue }}
    </div>
    <div
      v-if="!!value"
      :style="assetStyle"
      :class="assetPadding ? 'mr-1' : null"
      class="text-sm"
    >
      {{ t('percentage_display.symbol') }}
    </div>
  </div>
</template>
