<script setup lang="ts">
import type { EthStakingCombinedFilter, EthStakingFilter } from '@rotki/common';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { useEthStakingFilterFields } from '@/modules/staking/eth/use-eth-staking-filter-fields';
import { useEthStakingSelection } from '@/modules/staking/eth/use-eth-staking-selection';
import { useEthStakingSelectionFields } from '@/modules/staking/eth/use-eth-staking-selection-fields';

const selection = defineModel<EthStakingFilter>({ required: true });
const filter = defineModel<EthStakingCombinedFilter | undefined>('filter', { required: true });

const { modelMatches } = useEthStakingSelection(selection, filter);

// Validators picked by hand leave a status filter nothing to narrow, so the field is not offered.
const disableStatus = computed<boolean>(() => {
  const model = get(selection);
  return 'validators' in model && model.validators.length > 0;
});

const selectionFields = useEthStakingSelectionFields();
const filterFields = useEthStakingFilterFields(disableStatus);
const pillLabels = usePillBarLabels();

const fields = computed<FieldDef[]>(() => [...get(selectionFields), ...get(filterFields)]);
</script>

<template>
  <!--
    The bar draws a border but no surface of its own: it sits straight on the page background here,
    not inside a card, so it brings the surface its own pills already assume.
  -->
  <PillFilterBar
    v-model:matches="modelMatches"
    class="bg-white dark:bg-rui-grey-900"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
