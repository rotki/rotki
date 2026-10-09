<script lang="ts" setup>
const usageAnalytics = defineModel<boolean>('submitUsageAnalytics', { required: true });

defineProps<{
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="space-y-6">
    <p class="text-body-1 text-rui-text-secondary">
      {{ t('create_account.usage_analytics.description') }}
    </p>

    <RuiCheckbox
      v-model="usageAnalytics"
      :disabled="loading"
      color="primary"
      hide-details
    >
      {{ t('create_account.usage_analytics.label_confirm') }}
    </RuiCheckbox>
  </div>
</template>
