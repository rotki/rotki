<template>
  <create-account-form
    :loading="loading"
    :error="errorMessage"
    @error:clear="errorMessage = ''"
    @cancel="navigateToLogin()"
    @confirm="createNewAccount($event)"
  />
</template>

<script setup lang="ts">
import CreateAccountForm from '@/components/account-management/CreateAccountForm.vue';
import { usePremiumReminder } from '@/composables/premium';
import { Routes } from '@/router/routes';
import { useSessionStore } from '@/store/session';
import { useSessionAuthStore } from '@/store/session/auth';
import { CreateAccountPayload } from '@/types/login';

const loading = ref(false);
const errorMessage = ref<string>('');

const { tc } = useI18n();
const router = useRouter();
const { showGetPremiumButton } = usePremiumReminder();
const sessionStore = useSessionStore();
const { createAccount } = sessionStore;
const { logged, loginComplete } = storeToRefs(useSessionAuthStore());

const navigateToLogin = async () => await router.push(Routes.USER_LOGIN);

const createNewAccount = async (payload: CreateAccountPayload) => {
  set(loading, true);
  set(errorMessage, '');
  const result = await createAccount(payload);
  set(loading, false);

  if (result.success) {
    if (get(logged)) {
      showGetPremiumButton();
      set(loginComplete, true);
    }
  } else {
    set(
      errorMessage,
      result.message ?? tc('account_management.creation.error')
    );
  }
};
</script>

<style module lang="scss">
//
</style>
