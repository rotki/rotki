<script setup lang="ts">
import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import AccountManagementAside from '@/modules/auth/AccountManagementAside.vue';
import AccountManagementFooterText from '@/modules/auth/AccountManagementFooterText.vue';
import AdaptiveFooterButton from '@/modules/auth/AdaptiveFooterButton.vue';
import CreateAccountWizard from '@/modules/auth/create-account/CreateAccountWizard.vue';
import { useCreateAccountSteps } from '@/modules/auth/create-account/use-create-account-steps';
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
const { clearErrors, createNewAccount, error, loading } = useAccountManagement();

const step = ref<number>(1);
const mode = ref<CreateAccountMode>();

const { steps } = useCreateAccountSteps(mode);

onMounted(() => clearErrors());
</script>

<template>
  <section class="w-full flex flex-col flex-1 overflow-auto">
    <div class="h-full grow flex flex-col">
      <RotkiLogo
        class="my-5 lg:hidden w-full max-w-110 mx-auto max-[487px]:px-4 max-[487px]:max-w-full"
        unique-key="1b"
      />
      <!-- top aligned rather than centred like login, so the heading stays put as the steps change height -->
      <div class="flex flex-col grow px-4 pt-10 lg:pt-20 pb-6">
        <!-- fills the height so the connection wait can centre in it, while the wizard stays at the top -->
        <div
          data-testid="account-management"
          class="grow flex flex-col"
        >
          <UserHost>
            <UpgradeProgressDisplay v-if="upgradeVisible" />
            <CreateAccountWizard
              v-else
              v-model:step="step"
              v-model:mode="mode"
              :loading="loading"
              :error="error"
              @clear-error="clearErrors()"
              @cancel="navigateToUserLogin()"
              @confirm="createNewAccount($event)"
            />
          </UserHost>
        </div>
      </div>
      <!-- the side stepper shows progress on large screens -->
      <div class="lg:hidden w-full max-w-110 mx-auto px-4">
        <RuiFooterStepper
          :model-value="step"
          :pages="steps.length"
          variant="pill"
        />
      </div>
      <footer class="p-6 lg:p-8 flex items-center gap-3">
        <AccountManagementFooterText #default="{ copyright }">
          {{ copyright }}
        </AccountManagementFooterText>
        <AdaptiveFooterButton />
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
