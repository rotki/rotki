<script lang="ts" setup>
import { blockchainBalanceParams, useBlockchainBalanceFields } from '@/modules/balances/use-blockchain-balance-fields';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';

const chains = defineModel<string[]>('chains', { required: true });
const search = defineModel<string>('search', { required: true });

const fields = useBlockchainBalanceFields();
const pillLabels = usePillBarLabels();

/**
 * Written through by the bar, but owned by the page: the chain list decides what is aggregated as
 * well as what is filtered, so the page keeps both refs.
 */
const params = blockchainBalanceParams(chains, search);
</script>

<template>
  <PillFilterBar
    v-model:params="params"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
