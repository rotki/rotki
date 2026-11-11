<script lang="ts" setup>
import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import type { LoginCredentials } from '@/modules/auth/login';
import CreateAccountStepActions from '@/modules/auth/create-account/CreateAccountStepActions.vue';
import CreateAccountCredentialsForm
  from '@/modules/auth/create-account/credentials/CreateAccountCredentialsForm.vue';
import { useStepCheck } from '@/modules/auth/create-account/use-step-check';

const form = defineModel<LoginCredentials>('form', { required: true });
const passwordConfirm = defineModel<string>('passwordConfirm', { required: true });
const userPrompted = defineModel<boolean>('userPrompted', { required: true });

const { loading, mode = 'create' } = defineProps<{
  mode?: CreateAccountMode;
  loading: boolean;
}>();

const emit = defineEmits<{
  back: [];
  next: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const credentials = useTemplateRef<InstanceType<typeof CreateAccountCredentialsForm>>('credentials');

const { issueCount, validate } = useStepCheck(credentials);

const isRestoreMode = computed<boolean>(() => mode === 'restore');

async function next(): Promise<void> {
  if (await validate())
    emit('next');
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <RuiAlert
      v-if="isRestoreMode"
      type="warning"
      data-testid="create-account-restore-password-warning"
    >
      {{ t('create_account.credentials.password_sync_requirement') }}
    </RuiAlert>
    <p
      v-else
      class="text-body-1 text-rui-text-secondary"
    >
      {{ t('create_account.credentials.description') }}
    </p>
    <CreateAccountCredentialsForm
      ref="credentials"
      v-model:form="form"
      v-model:password-confirm="passwordConfirm"
      v-model:user-prompted="userPrompted"
      :loading="loading"
    />
    <CreateAccountStepActions
      :next-label="t('common.actions.continue')"
      next-test-id="create-account-credentials-continue"
      :issue-count="issueCount"
      :loading="loading"
      @back="emit('back')"
      @next="next()"
    />
  </div>
</template>
