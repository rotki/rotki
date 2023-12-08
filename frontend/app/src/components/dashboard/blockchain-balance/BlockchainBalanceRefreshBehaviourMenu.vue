<script setup lang="ts">
import { BlockchainRefreshButtonBehaviour } from '@/types/settings/frontend-settings';

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
    </VListItem>
  </VList>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>
