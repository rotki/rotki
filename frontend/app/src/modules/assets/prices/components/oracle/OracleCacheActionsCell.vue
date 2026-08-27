<script setup lang="ts">
const { disabled = false } = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        color="primary"
        variant="text"
        icon
        :disabled="disabled"
        @click="emit('click')"
      >
        <RuiIcon
          size="16"
          name="lu-trash-2"
        />
      </RuiButton>
    </template>
    {{ t('oracle_prices.cache.delete.tooltip') }}
  </RuiTooltip>
</template>
