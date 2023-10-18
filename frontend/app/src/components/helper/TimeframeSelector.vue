<script setup lang="ts">
import {
  TimeFramePersist,
  type TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';

const props = defineProps<{
  value: TimeFrameSetting;
  visibleTimeframes: TimeFrameSetting[];
  disabled?: boolean;
}>();

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
const css = useCssModule();
</script>

<template>
  <div :class="css.timeframe_selector">
    <RuiTooltip v-if="!premium" :popper="{ placement: 'top' }">
      <template #activator>
        <RuiIcon class="-ml-4" size="16" name="lock-2-fill" />
      </template>
      <span v-text="t('overall_balances.premium_hint')" />
    </RuiTooltip>
    <RuiButton
      v-for="(timeframe, i) in visibleTimeframes"
      :key="i"
      :color="activeClass(timeframe) ? 'primary' : 'secondary'"
      class="px-4"
      :disabled="(!premium && !worksWithoutPremium(timeframe)) || disabled"
      @click="input(timeframe)"
    >
      {{ timeframe }}
    </RuiButton>
  </div>
</template>

<style module lang="scss">
.timeframe_selector {
  @apply flex gap-4 items-center text-center;
}
</style>
