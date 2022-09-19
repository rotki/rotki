<template>
  <upgrade-row
    v-if="visible"
    :limit="limit"
    :total="total"
    :label="tc('eth2_validator_limit_row.label')"
    :colspan="colspan"
  />
</template>

<script lang="ts">
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';

export default defineComponent({
  name: 'Eth2ValidatorLimitRow',
  components: { UpgradeRow },
  props: {
    colspan: {
      required: true,
      type: Number
    }
  },
  setup() {
    const { eth2Validators } = storeToRefs(useEthAccountsStore());
    const limit = computed(() => get(eth2Validators).entriesLimit);
    const total = computed(() => get(eth2Validators).entriesFound);
    const visible = computed(
      () => limit.value > 0 && limit.value <= total.value
    );
    const { tc } = useI18n();
    return { limit, total, visible, tc };
  }
});
</script>
