<script lang="ts" setup>
const props = defineProps<{
  loading: boolean;
  submitUsageAnalytics: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:submit-usage-analytics', value: boolean): void;
}>();

const { t } = useI18n();

const usageAnalytics = useKebabVModel(props, 'submitUsageAnalytics', emit);
</script>

<template>
  <div class="space-y-8">
    <i18n-t
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
