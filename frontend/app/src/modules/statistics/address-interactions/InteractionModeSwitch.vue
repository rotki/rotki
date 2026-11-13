<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import { InteractionFilterMode } from './interaction-filter-mode';

const modelValue = defineModel<InteractionFilterMode>({ required: true });

defineProps<{
  icon: RuiIcons;
  label: string;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="inline-flex items-center gap-2">
    <span class="inline-flex items-center gap-1.5 text-xs font-medium text-rui-text-secondary">
      <RuiIcon
        :name="icon"
        size="14"
      />
      {{ label }}
    </span>
    <RuiButtonGroup
      v-model="modelValue"
      variant="segmented"
      required
      size="sm"
      :aria-label="label"
    >
      <RuiButton
        :model-value="InteractionFilterMode.INCLUDE"
        data-testid="interaction-mode-include"
      >
        {{ t('address_interactions.filter_mode.include') }}
      </RuiButton>
      <RuiButton
        :model-value="InteractionFilterMode.EXCLUDE"
        data-testid="interaction-mode-exclude"
      >
        {{ t('address_interactions.filter_mode.exclude') }}
      </RuiButton>
      <RuiButton
        :model-value="InteractionFilterMode.ONLY"
        data-testid="interaction-mode-only"
      >
        {{ t('address_interactions.filter_mode.only') }}
      </RuiButton>
    </RuiButtonGroup>
  </div>
</template>
