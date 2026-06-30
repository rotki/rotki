<script setup lang="ts">
import type { ConflictResolution } from '@/modules/assets/types';
import type { LoginCredentials } from '@/modules/auth/login';
import { startPromise } from '@shared/utils';
import AccountManagementAside from '@/modules/auth/AccountManagementAside.vue';
import AccountManagementFooterText from '@/modules/auth/AccountManagementFooterText.vue';
import AdaptiveFooterButton from '@/modules/auth/AdaptiveFooterButton.vue';
import LoginForm from '@/modules/auth/login/LoginForm.vue';
import NewReleaseChangelog from '@/modules/auth/login/NewReleaseChangelog.vue';
import WelcomeMessageDisplay from '@/modules/auth/login/WelcomeMessageDisplay.vue';
import LoginUnlockStage from '@/modules/auth/unlock-flow/LoginUnlockStage.vue';
import { UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';
import { useUnlockFlowController } from '@/modules/auth/unlock-flow/use-unlock-flow-controller';
import { useAccountManagement } from '@/modules/auth/use-account-management';
import UserHost from '@/modules/auth/UserHost.vue';
import { useDynamicMessages } from '@/modules/core/messaging/use-dynamic-messages';
import { useUpdateMessage } from '@/modules/core/messaging/use-update-message';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';
import { useLoginInitialChecks } from '@/pages/user/login/use-login-initial-checks';

definePage({
  meta: {
    layout: 'auth',
  },
});

const { t } = useI18n({ useScope: 'global' });
const { navigateToUserCreation } = useAppNavigation();
const { backendChanged } = useBackendManagement();
const { clearErrors, errors, loading, userLogin } = useAccountManagement();
const { applyUpdate, reset, skipUpdate, state, upgradeVisible } = useUnlockFlowController();
const { performInitialChecks } = useLoginInitialChecks();
const { activeWelcomeMessages, fetchMessages, welcomeHeader, welcomeMessage } = useDynamicMessages();
const { showReleaseNotes } = useUpdateMessage();

const isDocker = import.meta.env.VITE_DOCKER;

// The stage only takes over for phases that need their own UI (asset update + a DB upgrade
// during unlock). The login form stays mounted (with its loading state) through the transient
// authenticate/connect/unlock phases — so a wrong-password error and the typed password survive
// instead of remounting empty on the way back to the form.
const showStage = computed<boolean>(() => {
  const kind = get(state).kind;
  return kind === UnlockPhase.updatePrompt
    || kind === UnlockPhase.conflicts
    || kind === UnlockPhase.applyingUpdate
    || kind === UnlockPhase.restarting
    || (kind === UnlockPhase.unlocking && get(upgradeVisible));
});

const header = computed<{ header: string; text: string }>(() => {
  const header = get(welcomeHeader);
  return {
    header: header?.header || t('login.welcome_title'),
    text: header?.text || t('login.welcome_description'),
  };
});

async function handleLogin(credentials: LoginCredentials): Promise<void> {
  clearErrors();
  await userLogin(credentials);
}

function onConfirmUpdate(upToVersion: number): void {
  startPromise(applyUpdate(undefined, upToVersion));
}

function onResolveConflicts(resolution: ConflictResolution): void {
  startPromise(applyUpdate(resolution));
}

function onSkipUpdate(): void {
  startPromise(skipUpdate());
}

onMounted(async () => {
  // The flow is a shared singleton that survives logout; clear any terminal state from a
  // previous session so the form starts idle (not stuck in `ready`/loading or blocked by canStart).
  reset();
  fetchMessages();
  await performInitialChecks();
});
</script>

<template>
  <section class="w-full flex flex-col flex-1 overflow-auto">
    <div class="h-full grow flex flex-col">
      <RotkiLogo
        class="my-5 lg:hidden max-w-[27.5rem] mx-auto max-[487px]:px-4 max-[487px]:max-w-full"
        unique-key="0"
      />
      <div class="flex flex-col justify-start lg:justify-center max-w-full grow px-4 pt-10 pb-6">
        <div data-cy="account-management">
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
              @confirm="onConfirmUpdate($event)"
              @resolve="onResolveConflicts($event)"
              @skip="onSkipUpdate()"
            />
          </UserHost>
        </div>
      </div>
      <footer class="p-6 lg:p-8 flex items-center justify-between">
        <AccountManagementFooterText #default="{ copyright }">
          {{ copyright }}
        </AccountManagementFooterText>
        <div class="ml-4">
          <AdaptiveFooterButton />
        </div>
      </footer>
    </div>
  </section>
  <AccountManagementAside>
    <span class="rounded-full p-4 bg-rui-primary/20 inline-block mb-6 lg:mb-10 xl:mb-20">
      <RotkiLogo
        size="2"
        unique-key="0"
      />
    </span>
    <h2 class="text-h3 font-light xl:text-h2 mb-6">
      {{ header.header }}
    </h2>
    <p class="text-body-2">
      {{ header.text }}
    </p>
    <NewReleaseChangelog
      v-if="showReleaseNotes"
      class="mt-4"
    />
    <WelcomeMessageDisplay
      v-else-if="welcomeMessage"
      class="mt-6"
      :messages="activeWelcomeMessages"
    />
  </AccountManagementAside>
</template>
