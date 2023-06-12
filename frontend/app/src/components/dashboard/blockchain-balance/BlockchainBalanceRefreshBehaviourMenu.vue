<script setup lang="ts">
import { BlockchainRefreshButtonBehaviour } from '@/types/frontend-settings';

const { blockchainRefreshButtonBehaviour } = storeToRefs(
  useFrontendSettingsStore()
);

const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <v-list>
    <v-list-item
      :class="css['filter-heading']"
      class="font-weight-bold text-uppercase py-2"
    >
      {{ t('dashboard.blockchain_balances.behaviour.title') }}:
    </v-list-item>
    <v-list-item class="pb-2">
      <settings-option
        #default="{ update }"
        setting="blockchainRefreshButtonBehaviour"
        frontend-setting
      >
        <v-radio-group
          :value="blockchainRefreshButtonBehaviour"
          class="mt-0"
          hide-details
          @change="update($event)"
        >
          <v-radio
            :value="BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES"
            :label="
              t('dashboard.blockchain_balances.behaviour.only_refresh_balances')
            "
          />
          <v-radio
            :value="BlockchainRefreshButtonBehaviour.REDETECT_TOKENS"
            :label="
              t('dashboard.blockchain_balances.behaviour.redetect_tokens')
            "
          />
        </v-radio-group>
      </settings-option>
    </v-list-item>
  </v-list>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>
