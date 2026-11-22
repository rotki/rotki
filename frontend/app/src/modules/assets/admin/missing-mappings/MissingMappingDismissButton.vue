<script setup lang="ts">
const emit = defineEmits<{ dismiss: [] }>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :open-delay="300"
    :close-delay="0"
    :class-names="{ tooltip: 'max-w-80' }"
  >
    <template #activator>
      <RuiButton
        size="sm"
        variant="text"
        icon
        data-testid="row-dismiss"
        :aria-label="t('asset_management.cex_mapping.dismiss')"
        @click="emit('dismiss')"
      >
        <RuiIcon
          size="16"
          name="lu-x"
        />
      </RuiButton>
    </template>
    {{ t('asset_management.cex_mapping.dismiss_hint') }}
  </RuiTooltip>
</template>
