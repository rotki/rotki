<script setup lang="ts">
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';

const { t } = useI18n();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const notUsd = computed(() => get(currencySymbol) !== CURRENCY_USD);
</script>

<template>
  <RuiTooltip
    v-if="notUsd"
    class="mx-2 text-rui-text-secondary"
    :popper="{ placement: 'top' }"
    :open-delay="400"
    tooltip-class="max-w-[10rem]"
  >
    <template #activator>
      <RuiIcon
        size="20"
        name="lu-info"
      />
    </template>
    <span>{{ t('price_accuracy_hint.tooltip') }}</span>
  </RuiTooltip>
</template>
