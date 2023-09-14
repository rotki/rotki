<script lang="ts" setup>
defineProps<{
  loading: boolean;
  submitUsageAnalytics: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:submit-usage-analytics', value: boolean): void;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-8">
    <i18n
      path="create_account.usage_analytics.description"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
      tag="div"
    />

    <RuiCheckbox
      :value="submitUsageAnalytics"
      :disabled="loading"
      color="primary"
      hide-details
      @input="emit('update:submit-usage-analytics', $event)"
    >
      {{ t('create_account.usage_analytics.label_confirm') }}
    </RuiCheckbox>
  </div>
</template>
