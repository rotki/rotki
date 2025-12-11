<script setup lang="ts">
import { TimeFramePersist, type TimeFrameSetting } from '@rotki/common';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { usePremium } from '@/composables/premium';
import { isPeriodAllowed } from '@/utils/settings';

const modelValue = defineModel<TimeFrameSetting>({ required: true });

defineProps<{
  visibleTimeframes: TimeFrameSetting[];
  disabled?: boolean;
}>();

const premium = usePremium();

function worksWithoutPremium(period: TimeFrameSetting): boolean {
  return isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;
}

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex gap-4 items-center text-center">
    <PremiumLock
      v-if="!premium"
      :tooltip="t('overall_balances.premium_hint')"
    />
    <RuiButtonGroup
      v-model="modelValue"
      :disabled="disabled"
      class="flex-wrap justify-center border border-rui-grey-200 dark:border-rui-grey-800 !divide-rui-grey-200 dark:!divide-rui-grey-800"
      active-color="primary"
      variant="text"
      required
    >
      <RuiButton
        v-for="(timeframe, i) in visibleTimeframes"
        :key="i"
        class="!px-4"
        :disabled="!premium && !worksWithoutPremium(timeframe)"
        :model-value="timeframe"
      >
        {{ timeframe }}
      </RuiButton>
    </RuiButtonGroup>
  </div>
</template>
