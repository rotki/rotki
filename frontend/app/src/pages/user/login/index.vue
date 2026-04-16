<script setup lang="ts">
import type { LoginCredentials } from '@/modules/auth/login';
import AccountManagementAside from '@/modules/auth/AccountManagementAside.vue';
import AccountManagementFooterText from '@/modules/auth/AccountManagementFooterText.vue';
import AdaptiveFooterButton from '@/modules/auth/AdaptiveFooterButton.vue';
import LoginForm from '@/modules/auth/login/LoginForm.vue';
import NewReleaseChangelog from '@/modules/auth/login/NewReleaseChangelog.vue';
import WelcomeMessageDisplay from '@/modules/auth/login/WelcomeMessageDisplay.vue';
import UpgradeProgressDisplay from '@/modules/auth/upgrade/UpgradeProgressDisplay.vue';
import { useAccountManagement } from '@/modules/auth/use-account-management';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import UserHost from '@/modules/auth/UserHost.vue';
import { useDynamicMessages } from '@/modules/core/messaging/use-dynamic-messages';
import { useUpdateMessage } from '@/modules/core/messaging/use-update-message';
import AssetUpdate from '@/modules/shell/app/AssetUpdate.vue';
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
const { navigateToDashboard, navigateToUserCreation } = useAppNavigation();
const { canRequestData } = storeToRefs(useSessionAuthStore());
const { backendChanged } = useBackendManagement();
const { errors, loading, userLogin, clearErrors } = useAccountManagement();

const {
  checkForAssetUpdate,
  performingInitialChecks,
  performInitialChecks,
  showUpgradeProgress,
} = useLoginInitialChecks(errors);

const isDocker = import.meta.env.VITE_DOCKER;

const { activeWelcomeMessages, fetchMessages, welcomeHeader, welcomeMessage } = useDynamicMessages();
const { showReleaseNotes } = useUpdateMessage();

const header = computed(() => {
  const header = get(welcomeHeader);

  return {
    header: header?.header || t('login.welcome_title'),
    text: header?.text || t('login.welcome_description'),
  };
});

async function handleLogin(credentials: LoginCredentials) {
  clearErrors();
  await userLogin(credentials);
}

function skipInitialAssetUpdate(): void {
  set(checkForAssetUpdate, false);
}

const { logged } = storeToRefs(useSessionAuthStore());

// Navigate to dashboard after successful login
watch(logged, async (isLogged) => {
  if (isLogged) {
    set(canRequestData, true);
    await navigateToDashboard();
    set(showReleaseNotes, false);
  }
});

onMounted(async () => {
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
            <div v-if="performingInitialChecks">
              <div class="flex justify-center items-center py-12">
                <RuiProgress
                  color="primary"
                  variant="indeterminate"
                  circular
                  size="48"
                />
              </div>
            </div>
            <div v-else-if="checkForAssetUpdate">
              <AssetUpdate
                headless
                @skip="skipInitialAssetUpdate()"
              />
            </div>
            <UpgradeProgressDisplay v-else-if="showUpgradeProgress" />
            <LoginForm
              v-else
              :loading="loading"
              :is-docker="isDocker"
              :errors="errors"
              @touched="clearErrors()"
              @login="handleLogin($event)"
              @backend-changed="backendChanged($event)"
              @new-account="navigateToUserCreation()"
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
