<script lang="ts" setup>
const usageAnalytics = defineModel<boolean>('submitUsageAnalytics', { required: true });

defineProps<{
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="space-y-8">
    <i18n-t
      scope="global"
      keypath="create_account.usage_analytics.description"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
      tag="div"
    />

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
