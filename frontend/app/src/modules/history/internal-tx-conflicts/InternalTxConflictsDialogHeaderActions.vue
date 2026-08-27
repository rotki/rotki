<script setup lang="ts">
const emit = defineEmits<{
  'toggle-settings': [];
  'pin': [];
  'close': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-1">
    <RuiTooltip
      :options="{ placement: 'bottom' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          @click="emit('toggle-settings')"
        >
          <RuiIcon name="lu-settings" />
        </RuiButton>
      </template>
      {{ t('internal_tx_conflicts.actions.settings') }}
    </RuiTooltip>
    <RuiTooltip
      :options="{ placement: 'bottom' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          @click="emit('pin')"
        >
          <RuiIcon name="lu-pin" />
        </RuiButton>
      </template>
      {{ t('internal_tx_conflicts.actions.pin') }}
    </RuiTooltip>
    <RuiButton
      variant="text"
      icon
      @click="emit('close')"
    >
      <RuiIcon name="lu-x" />
    </RuiButton>
  </div>
</template>
