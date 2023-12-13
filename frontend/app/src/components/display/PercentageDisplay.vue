<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    value?: string;
    justify?: 'end' | 'start';
    assetPadding?: number;
  }>(),
  {
    value: undefined,
    justify: 'end',
    assetPadding: 0
  }
);

const { assetPadding, value } = toRefs(props);
const { shouldShowPercentage } = storeToRefs(useSessionSettingsStore());

const displayValue = computed<string>(() => {
  if (!get(shouldShowPercentage)) {
    return (Math.random() * 100 + 1).toFixed(2);
  }

  if (!isDefined(value)) {
    return '-';
  }

  return get(value).replace('%', '');
});

const assetStyle = computed<Record<string, string | undefined>>(() => {
  if (!get(assetPadding)) {
    return {
      'max-width': '0ch'
    };
  }
  return {
    width: `${get(assetPadding) + 1}ch`,
    'text-align': 'start'
  };
});

const { t } = useI18n();
</script>

<template>
  <div
    class="flex percentage-display flex-nowrap"
    :class="{
      'justify-start': justify === 'start',
      'justify-end': justify === 'end'
    }"
  >
    <div
      class="percentage-display__amount"
      :class="{
        blur: !shouldShowPercentage,
        'text-end': justify === 'end',
        'text-start': justify === 'start'
      }"
    >
      {{ displayValue }}
    </div>
    <div
      v-if="!!value"
      :style="assetStyle"
      :class="assetPadding ? 'mr-1' : null"
      class="ml-1 text-sm"
    >
      {{ t('percentage_display.symbol') }}
    </div>
  </div>
</template>
