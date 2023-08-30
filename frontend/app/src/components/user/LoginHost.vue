<script setup lang="ts">
const { t } = useI18n();
const css = useCssModule();

const { autolog } = useAutoLogin();
const { isPackaged } = useInterop();
const { connectionFailure, connected, dockerRiskAccepted } = storeToRefs(
  useMainStore()
);

const isDocker = import.meta.env.VITE_DOCKER;
const hasAcceptedDockerRisk = logicAnd(dockerRiskAccepted, isDocker);
const loginIfConnected = logicOr(
  isPackaged,
  hasAcceptedDockerRisk,
  logicNot(isDocker)
);
const displayRouter = logicAnd(connected, loginIfConnected);
</script>

<template>
  <div :class="css.overlay">
    <div :class="css.overlay__scroll">
      <section :class="css.section">
        <div :class="css.container">
          <div :class="css.wrapper">
            <div class="pb-4" light data-cy="account-management">
              <DockerWarning v-if="!dockerRiskAccepted && isDocker" />
              <ConnectionLoading
                v-else-if="!connectionFailure"
                :connected="connected && !autolog"
              />
              <ConnectionFailureMessage v-else />
              <div
                v-if="displayRouter"
                data-cy="account-management-forms"
                :class="css.router"
              >
                <RouterView />
              </div>
            </div>
          </div>
          <footer :class="css.container__footer">
            <span :class="css.copyright">
              {{ t('app.copyright', { year: new Date().getFullYear() }) }}
            </span>
            <div>
              <template v-if="isPackaged || true">
                <OnboardingSettingsButton />
              </template>
              <template v-else>
                <AboutButton />
              </template>
            </div>
          </footer>
        </div>
      </section>
      <span class="border-b lg:border-l" />
      <section :class="[css.section, css.section__welcome]">
        <span :class="css.logo">
          <RuiLogo class="w-8 !h-8" />
        </span>
        <h2 class="text-h2 mb-6">{{ t('login.welcome_title') }}</h2>
        <p class="text-body-2">{{ t('login.welcome_description') }}</p>
        <p class="text-body-2 text-rui-primary">
          {{ t('login.welcome_update_message') }}
        </p>
      </section>
    </div>
  </div>
</template>

<style module lang="scss">
.overlay {
  &__scroll {
    @apply flex flex-col-reverse lg:flex-row w-full;
  }

  @apply block overflow-y-auto w-full h-screen min-h-screen fixed top-0 bottom-0;
}

.section {
  &__welcome {
    @apply max-w-[31rem] mx-auto lg:max-w-[29%] p-6 lg:p-12;
  }

  @apply relative w-full;
}

.container {
  &__footer {
    .copyright {
      letter-spacing: 0.025rem;
      @apply font-normal text-[0.875rem] leading-[1.4525rem] text-black/60;
    }

    @apply flex items-center justify-between p-8;
  }

  @apply lg:min-h-screen flex flex-col justify-center;
}

.wrapper {
  @apply flex flex-col justify-center max-w-full grow px-4 pt-10 pb-6;
}

.router {
  min-height: 150px;
}

.logo {
  @apply rounded-full p-4 bg-rui-primary/20 inline-block mb-6 lg:mb-10 xl:mb-40;
}
</style>
