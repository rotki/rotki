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
  <!-- a menu section, headed like the menu's other sections -->
  <div class="px-4 pt-2 pb-3">
    <div class="pb-2 text-caption uppercase tracking-wide text-rui-text-secondary">
      {{ t('dashboard.blockchain_balances.behaviour.title') }}
    </div>
    <SettingSelect
      control="radio"
      setting="blockchainRefreshButtonBehaviour"
      size="sm"
      hide-details
      key-attr="value"
      text-attr="label"
      :options="options"
    />
  </div>
</template>
