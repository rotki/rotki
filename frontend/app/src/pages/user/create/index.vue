<script setup lang="ts">
import CreateAccountForm from '@/components/account-management/CreateAccountForm.vue';

import Fragment from '@/components/helper/Fragment';
import UpgradeProgressDisplay from '@/components/account-management/upgrade/UpgradeProgressDisplay.vue';

const { upgradeVisible } = storeToRefs(useSessionAuthStore());
const { navigateToUserLogin } = useAppNavigation();
const { createNewAccount, error, loading } = useAccountManagement();
</script>

<template>
  <fragment>
    <upgrade-progress-display v-if="upgradeVisible" />
    <create-account-form
      v-else
      :loading="loading"
      :error="error"
      @error:clear="error = ''"
      @cancel="navigateToUserLogin()"
      @confirm="createNewAccount($event)"
    />
  </fragment>
</template>
