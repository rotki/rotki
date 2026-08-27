<script setup lang="ts">
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
