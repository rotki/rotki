<script lang="ts" setup>
import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import CreateAccountErrorAlert from '@/modules/auth/create-account/analytics/CreateAccountErrorAlert.vue';
import CreateAccountSubmitAnalytics
  from '@/modules/auth/create-account/analytics/CreateAccountSubmitAnalytics.vue';

const submitUsageAnalytics = defineModel<boolean>('submitUsageAnalytics', { required: true });

const {
  error = '',
  loading,
  mode,
} = defineProps<{
  loading: boolean;
  mode: CreateAccountMode;
  error?: string;
}>();

const emit = defineEmits<{
  back: [];
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const submitLabel = computed<string>(() =>
  mode === 'restore' ? t('create_account.actions.restore_account') : t('create_account.actions.create_account'),
);
</script>

<template>
  <div class="space-y-8">
    <CreateAccountSubmitAnalytics
      v-model:submit-usage-analytics="submitUsageAnalytics"
      :loading="loading"
    />
    <CreateAccountErrorAlert
      v-if="error"
      :error="error"
    />
    <div class="grid grid-cols-2 gap-4">
      <RuiButton
        size="lg"
        class="w-full"
        :disabled="loading"
        @click="emit('back')"
      >
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton
        data-testid="create-account-analytics-continue"
        size="lg"
        class="w-full"
        :disabled="loading"
        :loading="loading"
        color="primary"
        @click="emit('confirm')"
      >
        {{ submitLabel }}
      </RuiButton>
    </div>
  </div>
</template>
