<script setup lang="ts">
import { RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip :open-delay="200">
    <template #activator>
      <RuiIcon
        name="lu-thumbs-up"
        size="16"
        color="success"
      />
    </template>
    {{ t('asset_movement_matching.dialog.recommended') }}
  </RuiTooltip>
</template>
