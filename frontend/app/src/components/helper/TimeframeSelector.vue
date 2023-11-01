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

const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <div :class="css.timeframe_selector">
    <RuiTooltip v-if="!premium" :popper="{ placement: 'top' }">
      <template #activator>
        <RuiIcon
          class="-ml-4 text-rui-text-secondary"
          size="16"
          name="lock-2-fill"
        />
      </template>
      <span v-text="t('overall_balances.premium_hint')" />
    </RuiTooltip>
    <RuiButtonGroup
      :disabled="disabled"
      :value="value"
      gap="md"
      class="flex-wrap justify-center"
      required
      @input="input($event)"
    >
      <RuiButton
        v-for="(timeframe, i) in visibleTimeframes"
        :key="i"
        :color="timeframe === value ? 'primary' : 'grey'"
        class="px-4"
        :disabled="!premium && !worksWithoutPremium(timeframe)"
        :value="timeframe"
      >
        {{ timeframe }}
      </RuiButton>
    </RuiButtonGroup>
  </div>
</template>

<style module lang="scss">
.timeframe_selector {
  @apply flex gap-4 items-center text-center;
}
</style>
