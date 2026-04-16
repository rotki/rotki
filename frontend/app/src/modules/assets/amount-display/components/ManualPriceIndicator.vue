<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
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
