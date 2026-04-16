<script setup lang="ts">
import AccountManagementAside from '@/modules/auth/AccountManagementAside.vue';
import AccountManagementFooterText from '@/modules/auth/AccountManagementFooterText.vue';
import AdaptiveFooterButton from '@/modules/auth/AdaptiveFooterButton.vue';
import CreateAccountWizard from '@/modules/auth/create-account/CreateAccountWizard.vue';
import UpgradeProgressDisplay from '@/modules/auth/upgrade/UpgradeProgressDisplay.vue';
import { useAccountManagement } from '@/modules/auth/use-account-management';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import UserHost from '@/modules/auth/UserHost.vue';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';

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
  <section class="w-full flex flex-col flex-1 overflow-auto">
    <div class="h-full grow flex flex-col">
      <div class="flex flex-col px-4 pt-16 lg:pt-24 grow">
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
