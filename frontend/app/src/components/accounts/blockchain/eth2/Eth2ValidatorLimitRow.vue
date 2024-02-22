<script setup lang="ts">
defineProps<{
  colspan: number;
}>();

const { stakingValidatorsLimits } = storeToRefs(useBlockchainStore());
const limit = computed(() => get(stakingValidatorsLimits)?.limit ?? 0);
const total = computed(() => get(stakingValidatorsLimits)?.total ?? 0);
const visible = computed(() => limit.value > 0 && limit.value <= total.value);
const { t } = useI18n();
</script>

<template>
  <UpgradeRow
    v-if="visible"
    :limit="limit"
    :total="total"
    :label="t('eth2_validator_limit_row.label')"
    :colspan="colspan"
  />
</template>
