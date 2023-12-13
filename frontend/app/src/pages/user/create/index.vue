<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const isDocker = import.meta.env.VITE_DOCKER;
const { appVersion, dockerRiskAccepted } = storeToRefs(useMainStore());

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
  <Fragment>
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
                @cancel="navigateToUserLogin(true)"
                @confirm="createNewAccount($event)"
              />
            </UserHost>
          </div>
        </div>
        <div class="w-[420px] max-w-full mx-auto px-4 mt-8">
          <RuiFooterStepper
            :value="step"
            :pages="steps.length"
            variant="pill"
          />
        </div>
        <footer :class="css.container__footer">
          <AccountManagementFooterText
            #default="{ copyright }"
            class="lg:hidden"
          >
            {{ copyright }}
          </AccountManagementFooterText>
          <div class="ml-4">
            <AdaptiveFooterButton />
          </div>
        </footer>
      </div>
    </section>
    <AccountManagementAside class="hidden lg:flex justify-between">
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
        <DockerWarning v-if="!dockerRiskAccepted && isDocker" class="mt-8" />
      </div>
      <AccountManagementFooterText
        #default="{ copyright }"
        class="flex items-center justify-between flex-wrap p-10"
      >
        <span>
          {{ appVersion }}
        </span>
        <span>
          {{ copyright }}
        </span>
      </AccountManagementFooterText>
    </AccountManagementAside>
  </Fragment>
</template>

<style module lang="scss">
.section {
  @apply w-full flex flex-col flex-1 overflow-auto;
}

.container {
  @apply h-full grow flex flex-col;

  &__footer {
    @apply p-6 lg:p-8 flex items-center justify-between lg:justify-end;
  }
}

.wrapper {
  @apply flex flex-col px-4 pt-16 lg:pt-24 grow;
}
</style>
