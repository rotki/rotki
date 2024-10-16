<script setup lang="ts">
const accountForAssetsMovements = ref(false);
const { accountForAssetsMovements: enabled } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(accountForAssetsMovements, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    setting="accountForAssetsMovements"
    :error-message="t('account_settings.messages.account_for_assets_movements')"
  >
    <template #title>
      {{ t('accounting_settings.trade.titles.assets_movements') }}
    </template>
    <template #default="{ error, success, update }">
      <RuiSwitch
        v-model="accountForAssetsMovements"
        class="accounting-settings__account-for-assets-movements"
        :success-messages="success"
        :error-messages="error"
        :label="t('accounting_settings.trade.labels.account_for_assets_movements')"
        color="primary"
        @update:model-value="update($event)"
      />
    </template>
  </SettingsOption>
</template>
