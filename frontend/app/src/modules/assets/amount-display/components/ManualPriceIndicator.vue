<script setup lang="ts">
import { RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
    class="self-center mr-2 cursor-pointer"
  >
    <template #activator>
      <RuiIcon
        size="16"
        color="warning"
        name="lu-sparkles"
      />
    </template>

    {{ t('amount_display.manual_tooltip') }}
  </RuiTooltip>
</template>
