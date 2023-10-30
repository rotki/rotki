<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    value?: string | null;
    justify?: 'end' | 'start';
    assetPadding?: number;
  }>(),
  {
    value: null,
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
  <VRow
    no-gutters
    class="percentage-display flex-nowrap"
    :justify="justify"
    align="center"
  >
    <VCol
      :cols="justify === 'end' ? null : 'auto'"
      class="percentage-display__amount"
      :class="{
        'blur-content': !shouldShowPercentage,
        'text-end': justify === 'end',
        'text-start': justify !== 'start'
      }"
    >
      {{ displayValue }}
    </VCol>
    <VCol
      v-if="!!value"
      :style="assetStyle"
      :class="assetPadding ? 'mr-1' : null"
      class="ml-1 percentage-display__symbol"
      :cols="justify === 'start' ? null : 'auto'"
    >
      {{ t('percentage_display.symbol') }}
    </VCol>
  </VRow>
</template>

<style scoped lang="scss">
.percentage-display {
  &__amount {
    &.blur-content {
      filter: blur(0.75em);
    }
  }

  &__symbol {
    font-size: 0.8em;
  }
}
</style>
