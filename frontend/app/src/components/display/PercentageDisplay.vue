<template>
  <v-row
    no-gutters
    class="percentage-display flex-nowrap"
    :justify="justify"
    align="center"
  >
    <v-col
      :cols="justify === 'end' ? null : 'auto'"
      class="percentage-display__amount"
      :class="{
        'blur-content': !shouldShowPercentage,
        'text-end': justify === 'end',
        'text-start': justify !== 'start'
      }"
    >
      {{ displayValue }}
    </v-col>
    <v-col
      v-if="!!value"
      :style="assetStyle"
      :class="assetPadding ? 'mr-1' : null"
      class="ml-1 percentage-display__symbol text--secondary"
      :cols="justify === 'start' ? null : 'auto'"
    >
      {{ t('percentage_display.symbol') }}
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { useSessionSettingsStore } from '@/store/settings/session';

const props = defineProps({
  value: {
    required: false,
    type: String,
    default: null,
    validator: (value: any) => typeof value === 'string' || value === null
  },
  justify: {
    required: false,
    type: String as PropType<'end' | 'start'>,
    default: 'end',
    validator: (value: any) => {
      return ['end', 'start'].includes(value);
    }
  },
  assetPadding: {
    required: false,
    type: Number,
    default: 0,
    validator: (chars: number) => chars >= 0 && chars <= 5
  }
});

const { assetPadding, value } = toRefs(props);
const { shouldShowPercentage, scrambleData } = storeToRefs(
  useSessionSettingsStore()
);

const displayValue = computed<string>(() => {
  if (get(scrambleData) || !get(shouldShowPercentage)) {
    return (Math.random() * 100 + 1).toFixed(2);
  }

  if (!get(value)) {
    return '-';
  }

  return get(value).replace('%', '');
});

const assetStyle = computed<{ [key: string]: string | undefined }>(() => {
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
