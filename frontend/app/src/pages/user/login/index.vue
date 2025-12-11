<script setup lang="ts">
import type { LoginCredentials } from '@/types/login';
import AccountManagementAside from '@/components/account-management/AccountManagementAside.vue';
import AccountManagementFooterText from '@/components/account-management/AccountManagementFooterText.vue';
import AdaptiveFooterButton from '@/components/account-management/AdaptiveFooterButton.vue';
import LoginForm from '@/components/account-management/login/LoginForm.vue';
import NewReleaseChangelog from '@/components/account-management/login/NewReleaseChangelog.vue';
import WelcomeMessageDisplay from '@/components/account-management/login/WelcomeMessageDisplay.vue';
import UpgradeProgressDisplay from '@/components/account-management/upgrade/UpgradeProgressDisplay.vue';
import UserHost from '@/components/account-management/UserHost.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import AssetUpdate from '@/components/status/update/AssetUpdate.vue';
import { useBackendManagement } from '@/composables/backend';
import { useDynamicMessages } from '@/composables/dynamic-messages';
import { useInterop } from '@/composables/electron-interop';
import { useAppNavigation } from '@/composables/navigation';
import { useUpdateMessage } from '@/composables/update-message';
import { useAccountManagement } from '@/composables/user/account';
import { useUpdateChecker } from '@/modules/session/use-update-checker';
import { useMonitorStore } from '@/store/monitor';
import { useSessionAuthStore } from '@/store/session/auth';
import { useWebsocketStore } from '@/store/websocket';

definePage({
  meta: {
    layout: 'auth',
  },
});

const { t } = useI18n({ useScope: 'global' });
const { navigateToDashboard, navigateToUserCreation } = useAppNavigation();
const { canRequestData, checkForAssetUpdate, upgradeVisible } = storeToRefs(useSessionAuthStore());
const { backendChanged } = useBackendManagement();
const { errors, loading, userLogin } = useAccountManagement();
const { checkForUpdate } = useUpdateChecker();
const { isPackaged } = useInterop();
const { connect } = useWebsocketStore();
const { startTaskMonitoring } = useMonitorStore();

const initialChecksDone = ref<boolean>(false);
const performingInitialChecks = ref<boolean>(false);

const showUpgradeProgress = computed<boolean>(() => get(upgradeVisible) && get(errors).length === 0);

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
  set(errors, []);
  await userLogin(credentials);
}

function skipInitialAssetUpdate() {
  set(checkForAssetUpdate, false);
}

async function performInitialChecks() {
  set(performingInitialChecks, true);

  try {
    // Check for app updates before showing login form
    if (isPackaged)
      await checkForUpdate();

    // Connect to backend and start monitoring before showing asset update UI
    await connect();
    startTaskMonitoring(false);

    // Set checkForAssetUpdate to true first, so AssetUpdate component will be shown and can run its check
    set(checkForAssetUpdate, true);

    // Mark initial checks as done after setting checkForAssetUpdate
    // This ensures AssetUpdate component is shown with the flag already set
    set(initialChecksDone, true);
  }
  finally {
    set(performingInitialChecks, false);
  }
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
              @touched="errors = []"
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
