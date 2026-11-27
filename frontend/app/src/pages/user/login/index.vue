<script setup lang="ts">
import type { LoginCredentials } from '@/modules/auth/login';
import { onMounted } from 'vue';
import { definePage } from 'vue-router/experimental';
import AccountManagementFooterText from '@/modules/auth/AccountManagementFooterText.vue';
import AdaptiveFooterButton from '@/modules/auth/AdaptiveFooterButton.vue';
import LoginAside from '@/modules/auth/login/LoginAside.vue';
import LoginForm from '@/modules/auth/login/LoginForm.vue';
import { useLoginStage } from '@/modules/auth/login/use-login-stage';
import LoginUnlockStage from '@/modules/auth/unlock-flow/LoginUnlockStage.vue';
import { useAccountManagement } from '@/modules/auth/use-account-management';
import UserHost from '@/modules/auth/UserHost.vue';
import { useDynamicMessages } from '@/modules/core/messaging/use-dynamic-messages';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';
import { useLoginInitialChecks } from '@/pages/user/login/use-login-initial-checks';

definePage({
  meta: {
    layout: 'auth',
  },
});

const { navigateToUserCreation } = useAppNavigation();
const { backendChanged } = useBackendManagement();
const { clearErrors, errors, loading, userLogin } = useAccountManagement();
const { onConfirmUpdate, onResolveConflicts, onSkipUpdate, reset, showStage, state, updateAccepted } = useLoginStage();
const { performInitialChecks } = useLoginInitialChecks();
const { fetchMessages } = useDynamicMessages();

const isDocker = import.meta.env.VITE_DOCKER === 'true';

async function handleLogin(credentials: LoginCredentials): Promise<void> {
  clearErrors();
  await userLogin(credentials);
}

/**
 * Starts the login screen from a clean slate.
 *
 * @remarks
 * The unlock flow is a shared singleton that outlives a logout, so without the reset a previous
 * session's terminal state leaves the form stuck in `ready` or blocked by `canStart`.
 */
async function startLoginScreen(): Promise<void> {
  reset();
  fetchMessages();
  await performInitialChecks();
}

onMounted(startLoginScreen);
</script>

<template>
  <section class="w-full flex flex-col flex-1 overflow-auto">
    <div class="h-full grow flex flex-col">
      <RotkiLogo
        class="my-5 lg:hidden w-full max-w-120 mx-auto max-[512px]:px-4 max-[512px]:max-w-full"
        unique-key="0"
      />
      <div class="flex flex-col max-w-full grow px-4 pb-6">
        <div
          data-testid="account-management"
          class="grow flex flex-col"
        >
          <UserHost>
            <LoginForm
              v-if="!showStage"
              :loading="loading"
              :is-docker="isDocker"
              :errors="errors"
              @touched="clearErrors()"
              @login="handleLogin($event)"
              @backend-changed="backendChanged($event)"
              @new-account="navigateToUserCreation()"
            />
            <LoginUnlockStage
              v-else
              :state="state"
              :update-accepted="updateAccepted"
              @confirm="onConfirmUpdate($event)"
              @resolve="onResolveConflicts($event)"
              @skip="onSkipUpdate()"
              @leave-upgrade="reset()"
              @leave-update="reset()"
            />
          </UserHost>
        </div>
      </div>
      <footer class="p-6 lg:p-8 flex items-center gap-3">
        <AccountManagementFooterText #default="{ copyright }">
          {{ copyright }}
        </AccountManagementFooterText>
        <AdaptiveFooterButton />
      </footer>
    </div>
  </section>
  <LoginAside />
</template>
