<script setup lang="ts">
import {
  TimeFramePeriod,
  TimeFramePersist,
  type TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';

const props = defineProps<{
  value: TimeFrameSetting;
  visibleTimeframes: TimeFrameSetting[];
  disabled?: boolean;
}>();

const emit = defineEmits<{ (e: 'input', value: TimeFrameSetting): void }>();

const premium = usePremium();

const internalValue = computed({
  get() {
    return props.value;
  },
  set(value: string) {
    assert(
      isOfEnum(TimeFramePersist)(value) || isOfEnum(TimeFramePeriod)(value)
    );
    emit('input', value);
  }
});

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
      v-model="internalValue"
      :disabled="disabled"
      gap="md"
      class="flex-wrap justify-center"
      active-color="primary"
      required
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
