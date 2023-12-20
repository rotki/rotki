<script setup lang="ts">
import { BlockchainRefreshButtonBehaviour } from '@/types/settings/frontend-settings';

const { blockchainRefreshButtonBehaviour } = storeToRefs(
  useFrontendSettingsStore()
);

const { t } = useI18n();
</script>

<template>
  <div class="p-2">
    <div class="font-bold text-uppercase p-2 text-sm">
      {{ t('dashboard.blockchain_balances.behaviour.title') }}:
    </div>
    <div class="pb-2 px-3">
      <SettingsOption
        #default="{ update }"
        setting="blockchainRefreshButtonBehaviour"
        frontend-setting
      >
        <RuiRadioGroup
          :value="blockchainRefreshButtonBehaviour"
          color="primary"
          class="mt-0"
          hide-details
          @input="update($event)"
        >
          <RuiRadio
            :internal-value="
              BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES
            "
            :label="
              t('dashboard.blockchain_balances.behaviour.only_refresh_balances')
            "
          />
          <RuiRadio
            :internal-value="BlockchainRefreshButtonBehaviour.REDETECT_TOKENS"
            :label="
              t('dashboard.blockchain_balances.behaviour.redetect_tokens')
            "
          />
        </RuiRadioGroup>
      </SettingsOption>
    </div>
  </div>
</template>
