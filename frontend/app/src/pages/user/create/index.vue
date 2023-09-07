<script setup lang="ts">
const { appVersion } = storeToRefs(useMainStore());

const { upgradeVisible } = storeToRefs(useSessionAuthStore());
const { navigateToUserLogin } = useAppNavigation();
const { createNewAccount, error, loading } = useAccountManagement();

const { t } = useI18n();
const css = useCssModule();

const step: Ref<number> = ref(1);
const steps = [
  {
    title: t('create_account.steps.step_1.title'),
    description: t('create_account.steps.step_1.description')
  },
  {
    title: t('create_account.steps.step_2.title'),
    description: t('create_account.steps.step_2.description')
  },
  {
    title: t('create_account.steps.step_3.title'),
    description: t('create_account.steps.step_3.description')
  },
  {
    title: t('create_account.steps.step_4.title')
  }
];
</script>

<template>
  <div :class="css.overlay">
    <div :class="css.overlay__scroll">
      <section :class="css.section">
        <div :class="css.container">
          <div :class="css.wrapper">
            <div class="pb-4" data-cy="account-management">
              <UserHost>
                <UpgradeProgressDisplay v-if="upgradeVisible" />
                <CreateAccountWizard
                  v-else
                  :step.sync="step"
                  :loading="loading"
                  :error="error"
                  @error:clear="error = ''"
                  @cancel="navigateToUserLogin()"
                  @confirm="createNewAccount($event)"
                />
              </UserHost>
            </div>
          </div>
          <footer :class="css.container__footer">
            <div class="w-[400px] mx-auto">
              <RuiFooterStepper
                :model-value="step"
                :pages="steps.length"
                variant="pill"
              />
            </div>
            <div class="mt-8 flex justify-between lg:justify-end items-center">
              <span class="lg:hidden" :class="css.footer__text">
                {{ t('app.copyright', { year: new Date().getFullYear() }) }}
              </span>
              <div class="ml-4">
                <AdaptiveFooterButton />
              </div>
            </div>
          </footer>
        </div>
      </section>
      <span class="hidden lg:block border-l" />
      <section :class="[css.section, css.section__aside]">
        <div class="p-12">
          <div class="mb-10">
            <RuiLogo class="!h-8" text />
          </div>
          <div>
            <RuiStepper
              custom
              orientation="vertical"
              :step="step"
              :steps="steps"
            />
          </div>
          <DockerWarning class="mt-8" />
        </div>
        <div
          class="flex items-center justify-between flex-wrap p-10"
          :class="css.footer__text"
        >
          <span>
            {{ appVersion }}
          </span>
          <span>
            {{ t('app.copyright', { year: new Date().getFullYear() }) }}
          </span>
        </div>
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
  &__aside {
    @apply hidden lg:flex lg:max-w-[29%] flex-grow-0 lg:flex-1 flex-col justify-between;
  }

  @apply relative w-full flex flex-col flex-1;
}

.container {
  &__footer {
    @apply p-6;
  }

  @apply lg:min-h-screen h-full grow flex flex-col;
}

.wrapper {
  @apply flex flex-col pt-[6rem] grow;
}

.router {
  min-height: 150px;
}

.footer {
  &__text {
    letter-spacing: 0.025rem;
    @apply font-normal text-[0.875rem] leading-[1.4525rem] text-rui-text-secondary;
  }
}
</style>
