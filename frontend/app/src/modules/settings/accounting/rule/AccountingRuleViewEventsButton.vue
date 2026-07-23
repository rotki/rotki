<script setup lang="ts">
const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButton
    size="sm"
    color="primary"
    class="absolute rounded-full top-1/2 -transform -translate-y-1/2 right-3"
    @click="emit('click')"
  >
    {{ t('accounting_settings.rule.action_dialog.view_affected_events') }}
    <template #append>
      <RuiIcon
        name="lu-arrow-right"
        size="20"
      />
    </template>
  </RuiButton>
</template>
