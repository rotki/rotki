<script setup lang="ts">
const emit = defineEmits<{
  'accept': [];
  'mark-spam': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButtonGroup class="dark:!divide-rui-grey-800">
    <RuiTooltip
      :open-delay="300"
      :close-delay="0"
    >
      <template #activator>
        <RuiButton
          color="success"
          icon
          variant="text"
          class="m-auto !rounded-none"
          data-testid="accept-token"
          @click="emit('accept')"
        >
          <RuiIcon name="lu-check" />
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
          variant="text"
          class="m-auto !rounded-none"
          data-testid="mark-token-spam"
          @click="emit('mark-spam')"
        >
          <RuiIcon name="lu-octagon-alert" />
        </RuiButton>
      </template>
      {{ t('asset_table.newly_detected.mark_as_spam') }}
    </RuiTooltip>
  </RuiButtonGroup>
</template>
