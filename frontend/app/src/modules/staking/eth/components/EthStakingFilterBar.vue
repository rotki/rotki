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
  <PillFilterBar
    v-model:matches="modelMatches"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
