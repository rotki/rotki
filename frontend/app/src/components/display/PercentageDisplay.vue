<script setup lang="ts">
import { useSessionSettingsStore } from '@/store/settings/session';

const props = withDefaults(
  defineProps<{
    value?: string;
    justify?: 'end' | 'start';
    assetPadding?: number;
  }>(),
  {
    assetPadding: 0,
    justify: 'end',
    value: undefined,
  },
);

const { assetPadding, value } = toRefs(props);
const { shouldShowPercentage } = storeToRefs(useSessionSettingsStore());

const displayValue = computed<string>(() => {
  if (!get(shouldShowPercentage))
    return (Math.random() * 100 + 1).toFixed(2);

  if (!isDefined(value))
    return '-';

  return get(value).replace('%', '');
});

const assetStyle = computed<Record<string, string | undefined>>(() => {
  if (!get(assetPadding)) {
    return {
      'max-width': '0ch',
    };
  }
  return {
    'text-align': 'start',
    'width': `${get(assetPadding) + 1}ch`,
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
