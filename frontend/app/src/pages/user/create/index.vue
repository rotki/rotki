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
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
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

const { context } = useCreateAccountSteps(mode, step);

onMounted(() => clearErrors());
</script>

<template>
  <section class="w-full flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
    <div class="h-full grow flex flex-col">
      <RotkiLogo
        class="my-5 lg:hidden w-full max-w-120 mx-auto max-[512px]:px-4 max-[512px]:max-w-full"
        unique-key="1b"
      />
      <div class="flex flex-col grow px-4 pt-14 lg:pt-[calc(12vh+3.5rem)] pb-6">
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
      <footer class="p-6 lg:p-8 flex items-center gap-3">
        <AccountManagementFooterText #default="{ copyright }">
          {{ copyright }}
        </AccountManagementFooterText>
        <AdaptiveFooterButton />
      </footer>
    </div>
  </section>
  <AccountManagementAside>
    <RotkiLogo
      class="mb-10"
      size="2"
      unique-key="1"
      text
    />
    <div
      class="flex flex-col gap-3"
      data-testid="create-account-context"
    >
      <h2 class="text-h5">
        {{ context.title }}
      </h2>
      <p class="text-body-1 text-rui-text-secondary whitespace-pre-line">
        {{ context.body }}
      </p>
      <ExternalLink
        v-if="context.link"
        :text="context.link.text"
        :url="context.link.url"
      />
    </div>
  </AccountManagementAside>
</template>
