<script setup lang="ts">
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { assert, type EthStakingCombinedFilter } from '@rotki/common';
import { isValidStatus } from '@/modules/core/table/filters/use-eth-validator-filter';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { EthStakingFilterValueKeys, useEthStakingFilterFields } from '@/modules/staking/eth/use-eth-staking-filter-fields';

const filter = defineModel<EthStakingCombinedFilter | undefined>('filter', { required: true });

const { disableStatus = false } = defineProps<{
  /** Validators are picked by hand, so a status filter has nothing left to narrow. */
  disableStatus?: boolean;
}>();

const fields = useEthStakingFilterFields(() => disableStatus);
const pillLabels = usePillBarLabels();

/**
 * The bar speaks the flat keyword map; the page's model is the `EthStakingCombinedFilter` the
 * premium component reads. Bridging the two is all this component does.
 */
const matches = computed<MatchedKeywordWithBehaviour<string>>({
  get() {
    const model = get(filter);
    return {
      ...(model?.fromTimestamp ? { [EthStakingFilterValueKeys.START]: model.fromTimestamp.toString() } : {}),
      ...(model?.toTimestamp ? { [EthStakingFilterValueKeys.END]: model.toTimestamp.toString() } : {}),
      ...(model?.status ? { [EthStakingFilterValueKeys.STATUS]: model.status } : {}),
    };
  },
  set(value) {
    const fromTimestamp = value[EthStakingFilterValueKeys.START];
    const toTimestamp = value[EthStakingFilterValueKeys.END];
    const status = value[EthStakingFilterValueKeys.STATUS];

    assert(typeof fromTimestamp === 'string' || fromTimestamp === undefined);
    assert(typeof toTimestamp === 'string' || toTimestamp === undefined);
    assert((typeof status === 'string' && isValidStatus(status)) || status === undefined);

    set(filter, {
      fromTimestamp: fromTimestamp ? Number(fromTimestamp) : undefined,
      status,
      toTimestamp: toTimestamp ? Number(toTimestamp) : undefined,
    });
  },
});
</script>

<template>
  <!--
    The bar draws a border but no surface of its own: it sits straight on the page background here,
    not inside a card, so it brings the surface its own pills already assume.
  -->
  <PillFilterBar
    v-model:matches="matches"
    class="bg-white dark:bg-rui-grey-900"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
