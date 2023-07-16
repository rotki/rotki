<script setup lang="ts">
defineProps({
  colspan: {
    required: true,
    type: Number
  }
});

const { eth2Validators } = storeToRefs(useEthAccountsStore());
const limit = computed(() => get(eth2Validators).entriesLimit);
const total = computed(() => get(eth2Validators).entriesFound);
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
