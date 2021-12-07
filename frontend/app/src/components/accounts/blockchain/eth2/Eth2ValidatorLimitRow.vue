<template>
  <upgrade-row
    v-if="visible"
    :limit="limit"
    :total="total"
    :label="$t('eth2_validator_limit_row.label')"
    :colspan="colspan"
  />
</template>

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useStore } from '@/store/utils';
import { assert } from '@/utils/assertions';

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
    const store = useStore();

    const balances = store.state.balances;
    assert(balances);
    const limit = computed(() => balances.eth2Validators.entriesLimit);
    const total = computed(() => balances.eth2Validators.entriesFound);
    const visible = computed(
      () => limit.value > 0 && limit.value <= total.value
    );
    return { limit, total, visible };
  }
});
</script>
