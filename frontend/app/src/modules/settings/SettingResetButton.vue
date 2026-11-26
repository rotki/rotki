<script setup lang="ts">
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';

const emit = defineEmits<{
  click: [];
}>();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
    :class-names="{ tooltip: 'max-w-48' }"
  >
    <template #activator>
      <RuiButton
        variant="text"
        icon
        @click="emit('click')"
      >
        <RuiIcon name="lu-refresh-ccw" />
      </RuiButton>
    </template>
    <span>{{ t('backend_settings.actions.reset') }}</span>
  </RuiTooltip>
</template>
