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
</script>

<template>
  <div class="flex gap-4 items-center text-center">
    <PremiumLock
      v-if="!premium"
      :tooltip="t('overall_balances.premium_hint')"
    />
    <RuiButtonGroup
      :disabled="disabled"
      :value="value"
      gap="md"
      class="flex-wrap justify-center"
      active-color="primary"
      required
      @input="input($event)"
    >
      <template #default>
        <RuiButton
          v-for="(timeframe, i) in visibleTimeframes"
          :key="i"
          class="px-4"
          :disabled="!premium && !worksWithoutPremium(timeframe)"
          :value="timeframe"
        >
          {{ timeframe }}
        </RuiButton>
      </template>
    </RuiButtonGroup>
  </div>
</template>
