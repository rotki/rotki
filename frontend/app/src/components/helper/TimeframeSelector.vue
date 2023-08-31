<script setup lang="ts">
import {
  TimeFramePersist,
  type TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { type PropType } from 'vue';

const props = defineProps({
  value: { required: true, type: String as PropType<TimeFrameSetting> },
  disabled: { required: false, type: Boolean, default: false },
  visibleTimeframes: {
    required: true,
    type: Array as PropType<TimeFrameSetting[]>
  }
});

const emit = defineEmits<{ (e: 'input', value: TimeFrameSetting): void }>();

const { value } = toRefs(props);
const input = (_value: TimeFrameSetting) => {
  emit('input', _value);
};

const premium = usePremium();

const worksWithoutPremium = (period: TimeFrameSetting): boolean =>
  isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;

const activeClass = (timeframePeriod: TimeFrameSetting): string =>
  timeframePeriod === get(value) ? 'timeframe-selector--active' : '';

const { t } = useI18n();
</script>

<template>
  <div class="timeframe-selector text-center">
    <VTooltip v-if="!premium" top>
      <template #activator="{ on, attrs }">
        <VIcon
          class="timeframe-selector__premium"
          small
          v-bind="attrs"
          v-on="on"
        >
          mdi-lock
        </VIcon>
      </template>
      <span v-text="t('overall_balances.premium_hint')" />
    </VTooltip>
    <VChip
      v-for="(timeframe, i) in visibleTimeframes"
      :key="i"
      :class="activeClass(timeframe)"
      class="ma-2 px-4"
      :disabled="(!premium && !worksWithoutPremium(timeframe)) || disabled"
      label
      @click="input(timeframe)"
    >
      {{ timeframe }}
    </VChip>
  </div>
</template>

<style scoped lang="scss">
.timeframe-selector {
  &--active {
    color: white !important;
    background-color: var(--v-primary-base) !important;
  }

  &__premium {
    margin-left: -16px;
  }
}
</style>
