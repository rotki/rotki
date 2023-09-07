<script setup lang="ts">
import { type LoginCredentials } from '@/types/login';

const { navigateToUserCreation, navigateToDashboard } = useAppNavigation();
const { upgradeVisible, canRequestData } = storeToRefs(useSessionAuthStore());
const { backendChanged } = useBackendManagement();
const { userLogin, errors, loading } = useAccountManagement();
const { checkForAssetUpdate } = storeToRefs(useSessionStore());

const showUpgradeProgress: ComputedRef<boolean> = computed(
  () => get(upgradeVisible) && get(errors).length === 0
);

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
</script>

<template>
  <div :class="css.overlay">
    <div :class="css.overlay__scroll">
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
            <span :class="css.copyright">
              {{ t('app.copyright', { year: new Date().getFullYear() }) }}
            </span>
            <div class="ml-4">
              <AdaptiveFooterButton />
            </div>
          </footer>
        </div>
      </section>
      <span class="border-b lg:border-l" />
      <section :class="[css.section, css.section__welcome]">
        <div>
          <span :class="css.logo">
            <RuiLogo class="w-8 !h-8" />
          </span>
          <h2 class="text-h2 mb-6">{{ t('login.welcome_title') }}</h2>
          <p class="text-body-2">{{ t('login.welcome_description') }}</p>
          <p v-if="false" class="text-body-2 text-rui-primary">
            {{ t('login.welcome_update_message') }}
          </p>
        </div>
        <DockerWarning class="mt-8" />
      </section>
    </div>
  </div>
</template>

<style module lang="scss">
.overlay {
  &__scroll {
    @apply flex flex-col-reverse lg:flex-row w-full min-h-screen;
  }

  @apply block overflow-y-auto w-full h-screen min-h-screen fixed top-0 bottom-0;
}

.section {
  &__welcome {
    @apply max-w-[31rem] mx-auto lg:max-w-[29%] p-6 lg:p-12 flex-grow-0 lg:flex-1 items-start;
  }

  @apply relative w-full flex flex-col flex-1;
}

.container {
  &__footer {
    .copyright {
      letter-spacing: 0.025rem;
      @apply font-normal text-[0.875rem] leading-[1.4525rem] text-rui-text-secondary;
    }

    @apply flex items-center justify-between p-6 lg:p-8;
  }

  @apply lg:min-h-screen h-full grow flex flex-col justify-center;
}

.wrapper {
  @apply flex flex-col justify-start lg:justify-center max-w-full grow px-4 pt-10 pb-6;
}

.router {
  min-height: 150px;
}

.logo {
  @apply rounded-full p-4 bg-rui-primary/20 inline-block mb-6 lg:mb-10 xl:mb-40;
}
</style>
