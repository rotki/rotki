<script lang="ts" setup>
const submitUsageAnalytics = defineModel<boolean>({ required: true });

defineProps<{
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCheckbox
    v-model="submitUsageAnalytics"
    :disabled="loading"
    color="primary"
    details="hidden"
    data-testid="create-account-usage-analytics"
  >
    <span class="flex flex-col">
      <span class="font-medium">{{ t('create_account.usage_analytics.label_confirm') }}</span>
      <span class="text-rui-text-secondary">{{ t('create_account.usage_analytics.description') }}</span>
    </span>
  </RuiCheckbox>
</template>
