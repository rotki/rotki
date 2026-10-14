<script setup lang="ts">
import type { LidoCsmNodeOperator } from '@/modules/staking/staking-types';
import { type BigNumber, Zero } from '@rotki/common';
import StakingTotals, { type StakingTotal } from '@/modules/staking/components/StakingTotals.vue';
import { STETH_IDENTIFIER } from '@/modules/staking/lido-csm/constants';

/**
 * The tracked node operators' figures added up, read before the table: the bond held, the part of
 * it that can be claimed, and the rewards not yet claimed. Operators whose metrics are not in yet
 * add nothing.
 */
const { operators } = defineProps<{
  operators: LidoCsmNodeOperator[];
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

interface Sums {
  bond: BigNumber;
  claimable: BigNumber;
  rewards: BigNumber;
}

const sums = computed<Sums>(() => operators.reduce<Sums>((acc, { metrics }) => {
  if (!metrics)
    return acc;
  return {
    bond: acc.bond.plus(metrics.bond.current),
    claimable: acc.claimable.plus(metrics.bond.claimable),
    rewards: acc.rewards.plus(metrics.rewards.pending),
  };
}, { bond: Zero, claimable: Zero, rewards: Zero }));

const totals = computed<StakingTotal[]>(() => {
  const { bond, claimable, rewards } = get(sums);
  return [
    { amount: bond, key: 'bond', label: t('staking_page.lido_csm.totals.bond'), testid: 'lido-csm-total-bond' },
    { amount: claimable, key: 'claimable', label: t('staking_page.lido_csm.totals.claimable'), testid: 'lido-csm-total-claimable' },
    { amount: rewards, key: 'rewards', label: t('staking_page.lido_csm.totals.rewards'), testid: 'lido-csm-total-rewards' },
  ];
});
</script>

<template>
  <StakingTotals
    :asset="STETH_IDENTIFIER"
    :totals="totals"
    :loading="loading"
  />
</template>
