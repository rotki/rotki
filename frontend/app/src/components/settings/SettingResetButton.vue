<script setup lang="ts">
const emit = defineEmits<{ (e: 'click'): void }>();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
    tooltip-class="max-w-[12rem]"
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
