<script setup lang="ts">
import { type LoginCredentials } from '@/types/login';
import Fragment from '@/components/helper/Fragment';

const { navigateToUserCreation, navigateToDashboard } = useAppNavigation();
const { upgradeVisible, canRequestData } = storeToRefs(useSessionAuthStore());
const { backendChanged } = useBackendManagement();
const { userLogin, errors, loading } = useAccountManagement();
const { checkForAssetUpdate } = storeToRefs(useSessionStore());

const showUpgradeProgress: ComputedRef<boolean> = computed(
  () => get(upgradeVisible) && get(errors).length === 0
);

const isDocker = import.meta.env.VITE_DOCKER;
const { dockerRiskAccepted } = storeToRefs(useMainStore());

const { fetchMessages, welcomeHeader, welcomeMessage } = useDynamicMessages();

const header = computed(() => {
  const header = get(welcomeHeader);

  return {
    header: header?.header || t('login.welcome_title'),
    text: header?.text || t('login.welcome_description')
  };
});

const handleLogin = async (credentials: LoginCredentials) => {
  set(errors, []);
  await userLogin(credentials);
};

const navigate = async () => {
  set(canRequestData, true);
  await navigateToDashboard();
};

const { t } = useI18n();
const css = useCssModule();

onMounted(async () => fetchMessages());
</script>

<template>
  <Fragment>
    <section :class="css.section">
      <div :class="css.container">
        <div :class="css.wrapper">
          <div class="pb-4" data-cy="account-management">
            <UserHost>
              <div v-if="checkForAssetUpdate">
                <AssetUpdate
                  headless
                  @skip="navigate()"
                  @complete="checkForAssetUpdate = false"
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
        <footer :class="css.container__footer">
          <AccountManagementFooterText #default="{ copyright }">
            {{ copyright }}
          </AccountManagementFooterText>
          <div class="ml-4">
            <AdaptiveFooterButton />
          </div>
        </footer>
      </div>
    </section>
    <AccountManagementAside class="p-6 lg:p-12">
      <div>
        <span :class="css.logo">
          <RuiLogo class="w-8 !h-8" />
        </span>
        <h2 class="text-h3 font-light xl:text-h2 mb-6">
          {{ header.header }}
        </h2>
        <p class="text-body-2">{{ header.text }}</p>
        <p v-if="false" class="text-body-2 text-rui-primary">
          {{ t('login.welcome_update_message') }}
        </p>
        <WelcomeMessageDisplay
          v-if="welcomeMessage"
          class="mt-6"
          :message="welcomeMessage"
        />
      </div>
      <DockerWarning v-if="!dockerRiskAccepted && isDocker" class="mt-8" />
    </AccountManagementAside>
  </Fragment>
</template>

<style module lang="scss">
.section {
  @apply w-full flex flex-col flex-1 overflow-auto;
}

.container {
  &__footer {
    @apply p-6 lg:p-8 flex items-center justify-between;
  }

  @apply h-full grow flex flex-col;
}

.wrapper {
  @apply flex flex-col justify-start lg:justify-center max-w-full grow px-4 pt-10 pb-6;
}

.logo {
  @apply rounded-full p-4 bg-rui-primary/20 inline-block mb-6 lg:mb-10 xl:mb-40;
}

.footer {
  &__text {
    letter-spacing: 0.025rem;
    @apply font-normal text-sm leading-6 text-rui-text-secondary;
  }
}
</style>
