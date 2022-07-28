<template>
  <settings-option
    #default="{ error, success, update }"
    setting="accountForAssetsMovements"
    :error-message="
      $tc('account_settings.messages.account_for_assets_movements')
    "
  >
    <v-switch
      v-model="accountForAssetsMovements"
      class="accounting-settings__account-for-assets-movements"
      :success-messages="success"
      :error-messages="error"
      :label="$tc('accounting_settings.labels.account_for_assets_movements')"
      color="primary"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';

const accountForAssetsMovements = ref(false);
const { accountingSettings } = useSettings();

onMounted(() => {
  const settings = get(accountingSettings);
  set(accountForAssetsMovements, settings.accountForAssetsMovements);
});
</script>
