<script setup lang="ts">
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        type="button"
        variant="text"
        icon
        size="sm"
      >
        <RuiIcon
          :size="20"
          name="lu-circle-question-mark"
        />
      </RuiButton>
    </template>
    {{ t('underlying_token_manager.hint') }}
  </RuiTooltip>
</template>
