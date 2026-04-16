<script setup lang="ts">
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';

defineProps<{
  colspan: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const { validatorsLimitInfo } = useEthStaking();
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
