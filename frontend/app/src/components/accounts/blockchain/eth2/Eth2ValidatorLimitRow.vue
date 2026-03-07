<script setup lang="ts">
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';

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
