<script setup lang="ts">
import SettingSelect from '@/modules/settings/controls/SettingSelect.vue';
import { BlockchainRefreshButtonBehaviour } from '@/modules/settings/types/frontend-settings';

const { t } = useI18n({ useScope: 'global' });

const options = [
  {
    label: t('dashboard.blockchain_balances.behaviour.only_refresh_balances'),
    value: BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
  },
  {
    label: t('dashboard.blockchain_balances.behaviour.redetect_tokens'),
    value: BlockchainRefreshButtonBehaviour.REDETECT_TOKENS,
  },
];
</script>

<template>
  <div class="p-2">
    <div class="font-bold uppercase p-2 text-sm">
      {{ t('dashboard.blockchain_balances.behaviour.title') }}:
    </div>
    <div class="pb-2 px-3">
      <SettingSelect
        control="radio"
        setting="blockchainRefreshButtonBehaviour"
        class="mt-0"
        hide-details
        key-attr="value"
        text-attr="label"
        :options="options"
      />
    </div>
  </div>
</template>
