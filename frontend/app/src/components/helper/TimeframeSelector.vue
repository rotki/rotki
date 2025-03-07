<script setup lang="ts">
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { usePremium } from '@/composables/premium';
import { isOfEnum } from '@/utils';
import { isPeriodAllowed } from '@/utils/settings';
import { TimeFramePeriod, TimeFramePersist, type TimeFrameSetting } from '@rotki/common';

const props = defineProps<{
  modelValue: TimeFrameSetting;
  visibleTimeframes: TimeFrameSetting[];
  disabled?: boolean;
}>();

const emit = defineEmits<{ (e: 'update:model-value', value: TimeFrameSetting): void }>();

const premium = usePremium();

const internalValue = computed({
  get() {
    return props.modelValue;
  },
  set(value: string) {
    assert(isOfEnum(TimeFramePersist)(value) || isOfEnum(TimeFramePeriod)(value));
    emit('update:model-value', value);
  },
});

function worksWithoutPremium(period: TimeFrameSetting): boolean {
  return isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;
}

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
      <RuiButton
        v-for="(timeframe, i) in visibleTimeframes"
        :key="i"
        class="px-4"
        :disabled="!premium && !worksWithoutPremium(timeframe)"
        :model-value="timeframe"
      >
        {{ timeframe }}
      </RuiButton>
    </RuiButtonGroup>
  </div>
</template>
