<script lang="ts" setup>
import type { LoginCredentials } from '@/types/login';
import CreateAccountCredentialsForm
  from '@/components/account-management/create-account/credentials/CreateAccountCredentialsForm.vue';

withDefaults(
  defineProps<{
    syncDatabase?: boolean;
    loading: boolean;
    form: LoginCredentials;
    passwordConfirm: string;
    userPrompted: boolean;
  }>(),
  {
    syncDatabase: false,
  },
);

const emit = defineEmits<{
  (e: 'back'): void;
  (e: 'next'): void;
  (e: 'update:form', form: LoginCredentials): void;
  (e: 'update:password-confirm', value: string): void;
  (e: 'update:user-prompted', value: boolean): void;
}>();

const valid = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="space-y-6">
    <i18n-t
      scope="global"
      keypath="create_account.credentials.description"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
      tag="div"
    >
      <template #highlight>
        <strong>{{ t('create_account.credentials.highlight') }}</strong>
      </template>
    </i18n-t>
    <CreateAccountCredentialsForm
      v-model:valid="valid"
      class="mt-8"
      :form="form"
      :password-confirm="passwordConfirm"
      :user-prompted="userPrompted"
      :loading="loading"
      @update:form="emit('update:form', $event)"
      @update:password-confirm="emit('update:password-confirm', $event)"
      @update:user-prompted="emit('update:user-prompted', $event)"
    />
    <div>
      <RuiAlert
        v-if="syncDatabase"
        class="create-account__password-sync-requirement"
        type="warning"
      >
        {{ t('create_account.credentials.password_sync_requirement') }}
      </RuiAlert>
    </div>
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
        size="lg"
        class="w-full"
        data-cy="create-account__credentials__button__continue"
        :disabled="!valid || loading"
        :loading="loading"
        color="primary"
        @click="emit('next')"
      >
        {{ t('common.actions.continue') }}
      </RuiButton>
    </div>
  </div>
</template>
