<template>
  <login-form
    :loading="loading"
    :sync-conflict="syncConflict"
    :errors="errors"
    :show-upgrade-message="showUpgradeMessage"
    @touched="errors = []"
    @login="userLogin($event)"
    @backend-changed="backendChanged($event)"
    @new-account="navToUserCreation"
  />
</template>

<script setup lang="ts">
import LoginForm from '@/components/account-management/LoginForm.vue';
import { useBackendManagement } from '@/composables/backend';
import { usePremiumReminder } from '@/composables/premium';
import { Routes } from '@/router/routes';
import { useSessionStore } from '@/store/session';
import { useSessionAuthStore } from '@/store/session/auth';
import { LoginCredentials } from '@/types/login';
import { setLastLogin } from '@/utils/account-management';

const loading = ref(false);
const showUpgradeMessage = ref(false);
const errors = ref<string[]>([]);

const router = useRouter();
const { showGetPremiumButton } = usePremiumReminder();
const { logged, premiumPrompt, syncConflict } = storeToRefs(
  useSessionAuthStore()
);
const { login } = useSessionStore();
const { backendChanged } = useBackendManagement();

const userLogin = async ({
  username,
  password,
  syncApproval
}: LoginCredentials) => {
  set(loading, true);
  const result = await login({
    username,
    password,
    syncApproval
  });

  if (!result.success) {
    set(errors, [result.message]);
  }
  set(loading, false);
  if (get(logged)) {
    setLastLogin(username);
    set(premiumPrompt, true);
    showGetPremiumButton();
  }
};

const navToUserCreation = async () => {
  await router.push(Routes.USER_CREATE);
};

const { start, stop } = useTimeoutFn(
  () => {
    set(showUpgradeMessage, true);
  },
  15000,
  {
    immediate: false
  }
);

watch(loading, loading => {
  if (loading) {
    start();
  } else {
    stop();
    set(showUpgradeMessage, false);
  }
});
</script>
