<script setup lang="ts">
import { BlockchainRefreshButtonBehaviour } from '@/types/frontend-settings';

const { blockchainRefreshButtonBehaviour } = storeToRefs(
  useFrontendSettingsStore()
);

const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <VList>
    <VListItem
      :class="css['filter-heading']"
      class="font-bold text-uppercase py-2"
    >
      {{ t('dashboard.blockchain_balances.behaviour.title') }}:
    </VListItem>
    <VListItem class="pb-2">
      <SettingsOption
        #default="{ update }"
        setting="blockchainRefreshButtonBehaviour"
        frontend-setting
      >
        <VRadioGroup
          :value="blockchainRefreshButtonBehaviour"
          class="mt-0"
          hide-details
          @change="update($event)"
        >
          <VRadio
            :value="BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES"
            :label="
              t('dashboard.blockchain_balances.behaviour.only_refresh_balances')
            "
          />
          <VRadio
            :value="BlockchainRefreshButtonBehaviour.REDETECT_TOKENS"
            :label="
              t('dashboard.blockchain_balances.behaviour.redetect_tokens')
            "
          />
        </VRadioGroup>
      </SettingsOption>
    </VListItem>
  </VList>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>
