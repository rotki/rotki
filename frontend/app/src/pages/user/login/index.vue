<script setup lang="ts">
import LoginForm from '@/components/account-management/LoginForm.vue';
import { useSessionAuthStore } from '@/store/session/auth';
import Fragment from '@/components/helper/Fragment';
import { type LoginCredentials } from '@/types/login';
import AssetUpdate from '@/components/status/update/AssetUpdate.vue';
import PremiumReminder from '@/components/account-management/PremiumReminder.vue';
import UpgradeProgressDisplay from '@/components/account-management/upgrade/UpgradeProgressDisplay.vue';

const checkForAssetUpdate = ref(false);

const { navigateToUserCreation, navigateToDashboard } = useAppNavigation();
const { syncConflict, upgradeVisible, canRequestData } = storeToRefs(
  useSessionAuthStore()
);
const { backendChanged } = useBackendManagement();
const { userLogin, errors, loading } = useAccountManagement();
const { isPremiumDialogVisible } = usePremiumReminder();

const handleLogin = async (credentials: LoginCredentials) => {
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
        @skip="navigate"
        @complete="checkForAssetUpdate = false"
      />
    </div>
    <premium-reminder
      v-else-if="isPremiumDialogVisible"
      @dismiss="checkForAssetUpdate = true"
    />
    <upgrade-progress-display v-else-if="upgradeVisible" />
    <login-form
      v-else
      :loading="loading"
      :sync-conflict="syncConflict"
      :errors="errors"
      @touched="errors = []"
      @login="handleLogin($event)"
      @backend-changed="backendChanged($event)"
      @new-account="navigateToUserCreation()"
    />
  </fragment>
</template>
