<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';

const modelValue = defineModel<OverlayMode>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const options = computed<{ value: OverlayMode; label: string; icon: RuiIcons }[]>(() => [
  { icon: 'lu-eye-off', label: t('accounting_overlay.modes.none'), value: OverlayMode.NONE },
  { icon: 'lu-wallet', label: t('accounting_overlay.modes.balance'), value: OverlayMode.BALANCE },
]);
</script>

<template>
  <RuiTooltip :open-delay="300">
    <template #activator>
      <RuiButtonGroup
        v-model="modelValue"
        variant="outlined"
        color="primary"
        size="sm"
        data-testid="accounting-overlay-mode"
      >
        <RuiButton
          v-for="option in options"
          :key="option.value"
          :model-value="option.value"
          :aria-label="option.label"
        >
          <RuiIcon
            :name="option.icon"
            size="16"
          />
        </RuiButton>
      </RuiButtonGroup>
    </template>
    {{ t('accounting_overlay.tooltip') }}
  </RuiTooltip>
</template>
