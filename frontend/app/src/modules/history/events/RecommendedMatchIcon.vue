<script setup lang="ts">
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
