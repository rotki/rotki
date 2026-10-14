<script setup lang="ts">
const emit = defineEmits<{
  'accept': [];
  'mark-spam': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center justify-end gap-1">
    <RuiTooltip
      :open-delay="300"
      :close-delay="0"
    >
      <template #activator>
        <RuiButton
          color="success"
          icon
          size="sm"
          variant="text"
          :aria-label="t('asset_table.newly_detected.accept')"
          data-testid="accept-token"
          @click="emit('accept')"
        >
          <RuiIcon
            name="lu-check"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('asset_table.newly_detected.accept') }}
    </RuiTooltip>
    <RuiTooltip
      :open-delay="300"
      :close-delay="0"
    >
      <template #activator>
        <RuiButton
          color="error"
          icon
          size="sm"
          variant="text"
          :aria-label="t('asset_table.newly_detected.mark_as_spam')"
          data-testid="mark-token-spam"
          @click="emit('mark-spam')"
        >
          <RuiIcon
            name="lu-octagon-alert"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('asset_table.newly_detected.mark_as_spam') }}
    </RuiTooltip>
  </div>
</template>
