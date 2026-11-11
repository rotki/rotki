<script lang="ts" setup>
import type { CreateAccountStepId } from '@/modules/auth/create-account/types';
import CreateAccountStepActions from '@/modules/auth/create-account/CreateAccountStepActions.vue';
import CreateAccountErrorAlert from '@/modules/auth/create-account/errors/CreateAccountErrorAlert.vue';

const { apiKey, error = '', username } = defineProps<{
  apiKey: string;
  username: string;
  loading: boolean;
  error?: string;
}>();

const emit = defineEmits<{
  'back': [];
  'confirm': [];
  'go-to': [step: CreateAccountStepId];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Enough of the key to tell which one was entered, without showing it. */
const KEY_TAIL_LENGTH = 4;

const keyTail = computed<string>(() => apiKey.slice(-KEY_TAIL_LENGTH));

interface SummaryRow {
  label: string;
  value: string;
  step: CreateAccountStepId;
  testId: string;
}

const rows = computed<SummaryRow[]>(() => [
  {
    label: t('create_account.summary.premium'),
    step: 'premium',
    testId: 'create-account-summary-premium',
    value: t('create_account.summary.premium_value', { tail: get(keyTail) }),
  },
  {
    label: t('create_account.summary.profile'),
    step: 'profile',
    testId: 'create-account-summary-profile',
    value: username,
  },
]);
</script>

<template>
  <div class="flex flex-col gap-6">
    <dl class="rounded-md border border-rui-grey-300 dark:border-rui-grey-800 bg-white dark:bg-transparent divide-y divide-rui-grey-300 dark:divide-rui-grey-800">
      <div
        v-for="row in rows"
        :key="row.step"
        class="grid grid-cols-1 sm:grid-cols-[8rem_1fr] sm:items-center gap-x-3 gap-y-1 px-4 py-3"
        :data-testid="row.testId"
      >
        <dt class="text-rui-text-secondary">
          {{ row.label }}
        </dt>
        <dd class="flex items-center justify-between gap-3 min-w-0">
          <span class="min-w-0 wrap-anywhere">{{ row.value }}</span>
          <RuiButton
            variant="text"
            color="primary"
            class="shrink-0"
            type="button"
            :disabled="loading"
            @click="emit('go-to', row.step)"
          >
            {{ t('create_account.summary.change') }}
          </RuiButton>
        </dd>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-[8rem_1fr] gap-x-3 gap-y-1 px-4 py-3">
        <dt class="text-rui-text-secondary">
          {{ t('create_account.summary.what_happens') }}
        </dt>
        <dd>{{ t('create_account.summary.what_happens_value') }}</dd>
      </div>
    </dl>
    <CreateAccountErrorAlert
      v-if="error"
      :error="error"
    />
    <CreateAccountStepActions
      :next-label="t('create_account.actions.restore_profile')"
      next-test-id="create-account-submit"
      :loading="loading"
      @back="emit('back')"
      @next="emit('confirm')"
    />
  </div>
</template>
