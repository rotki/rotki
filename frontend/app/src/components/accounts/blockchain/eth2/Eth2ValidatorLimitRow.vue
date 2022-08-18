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
import { computed, defineComponent } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';

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
    const { eth2ValidatorsState } = storeToRefs(useBlockchainAccountsStore());
    const limit = computed(() => get(eth2ValidatorsState).entriesLimit);
    const total = computed(() => get(eth2ValidatorsState).entriesFound);
    const visible = computed(
      () => limit.value > 0 && limit.value <= total.value
    );
    const { tc } = useI18n();
    return { limit, total, visible, tc };
  }
});
</script>
