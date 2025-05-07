<script setup lang="ts">
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';

defineProps<{
  colspan: number;
}>();

const { validatorsLimitInfo } = useEthStaking();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <UpgradeRow
    v-if="validatorsLimitInfo.showWarning"
    :limit="validatorsLimitInfo.limit"
    :total="validatorsLimitInfo.total"
    :label="t('eth2_validator_limit_row.label')"
    :colspan="colspan"
  />
</template>
