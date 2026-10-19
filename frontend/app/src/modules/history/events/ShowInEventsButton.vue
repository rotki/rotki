<script setup lang="ts">
const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :open-delay="400"
    :options="{ placement: 'top' }"
  >
    <template #activator>
      <RuiButton
        size="sm"
        variant="outlined"
        icon
        color="primary"
        class="px-2! h-7.5"
        @click="emit('click')"
      >
        <RuiIcon
          size="16"
          name="lu-external-link"
        />
      </RuiButton>
    </template>
    {{ t('asset_movement_matching.dialog.show_in_events') }}
  </RuiTooltip>
</template>
