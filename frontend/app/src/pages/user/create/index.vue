<script setup lang="ts">
import AccountManagementAside from '@/components/account-management/AccountManagementAside.vue';
import AccountManagementFooterText from '@/components/account-management/AccountManagementFooterText.vue';
import AdaptiveFooterButton from '@/components/account-management/AdaptiveFooterButton.vue';
import CreateAccountWizard from '@/components/account-management/create-account/CreateAccountWizard.vue';
import UpgradeProgressDisplay from '@/components/account-management/upgrade/UpgradeProgressDisplay.vue';
import UserHost from '@/components/account-management/UserHost.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import { useAppNavigation } from '@/composables/navigation';
import { useAccountManagement } from '@/composables/user/account';
import { useSessionAuthStore } from '@/store/session/auth';

definePage({
  meta: {
    layout: 'auth',
  },
});

const { upgradeVisible } = storeToRefs(useSessionAuthStore());
const { navigateToUserLogin } = useAppNavigation();
const { createNewAccount, error, loading } = useAccountManagement();

const { t } = useI18n({ useScope: 'global' });

const step = ref<number>(1);
const steps = [
  {
    description: t('create_account.steps.step_1.description'),
    title: t('create_account.steps.step_1.title'),
  },
  {
    description: t('create_account.steps.step_2.description'),
    title: t('create_account.steps.step_2.title'),
  },
  {
    description: t('create_account.steps.step_3.description'),
    title: t('create_account.steps.step_3.title'),
  },
  {
    title: t('create_account.steps.step_4.title'),
  },
];
</script>

<template>
  <section :class="$style.section">
    <div :class="$style.container">
      <div :class="$style.wrapper">
        <div
          class="pb-4"
          data-cy="account-management"
        >
          <UserHost>
            <UpgradeProgressDisplay v-if="upgradeVisible" />
            <CreateAccountWizard
              v-else
              v-model:step="step"
              :loading="loading"
              :error="error"
              @clear-error="error = ''"
              @cancel="navigateToUserLogin(true)"
              @confirm="createNewAccount($event)"
            />
          </UserHost>
        </div>
      </div>
      <div class="w-[420px] max-w-full mx-auto px-4 mt-8">
        <RuiFooterStepper
          :model-value="step"
          :pages="steps.length"
          variant="pill"
        />
      </div>
      <footer :class="$style.container__footer">
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
    <div class="mb-10">
      <RotkiLogo
        size="2"
        unique-key="1"
        text
      />
    </div>
    <div>
      <RuiStepper
        custom
        orientation="vertical"
        :step="step"
        :steps="steps"
      />
    </div>
  </AccountManagementAside>
</template>

<style module lang="scss">
.section {
  @apply w-full flex flex-col flex-1 overflow-auto;
}

.container {
  @apply h-full grow flex flex-col;

  &__footer {
    @apply p-6 lg:p-8 flex items-center justify-between;
  }
}

.wrapper {
  @apply flex flex-col px-4 pt-16 lg:pt-24 grow;
}
</style>
