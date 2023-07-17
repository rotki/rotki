<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
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
</script>

<template>
  <Fragment>
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
  </Fragment>
</template>
