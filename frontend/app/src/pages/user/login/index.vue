<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { type LoginCredentials } from '@/types/login';

const checkForAssetUpdate = ref(false);

const { navigateToUserCreation, navigateToDashboard } = useAppNavigation();
const { upgradeVisible, canRequestData } = storeToRefs(useSessionAuthStore());
const { backendChanged } = useBackendManagement();
const { userLogin, errors, loading } = useAccountManagement();
const { isPremiumDialogVisible } = usePremiumReminder();

const showUpgradeProgress: ComputedRef<boolean> = computed(
  () => get(upgradeVisible) && get(errors).length === 0
);

const handleLogin = async (credentials: LoginCredentials) => {
  set(errors, []);
  const skipPremiumDisplay = await userLogin(credentials);
  if (skipPremiumDisplay) {
    set(checkForAssetUpdate, true);
  }
};

const navigate = async () => {
  set(canRequestData, true);
  await navigateToDashboard();
};
</script>

<template>
  <fragment>
    <div v-if="checkForAssetUpdate">
      <asset-update
        headless
        @skip="navigate()"
        @complete="checkForAssetUpdate = false"
      />
    </div>
    <premium-reminder
      v-else-if="isPremiumDialogVisible"
      @dismiss="checkForAssetUpdate = true"
    />
    <upgrade-progress-display v-else-if="showUpgradeProgress" />
    <login-form
      v-else
      :loading="loading"
      :errors="errors"
      @touched="errors = []"
      @login="handleLogin($event)"
      @backend-changed="backendChanged($event)"
      @new-account="navigateToUserCreation()"
    />
  </fragment>
</template>
