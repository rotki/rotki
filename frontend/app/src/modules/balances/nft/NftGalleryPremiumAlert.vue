<script setup lang="ts">
import PlanLimitMessage from '@/modules/premium/PlanLimitMessage.vue';

defineProps<{
  /** How many NFTs the plan shows; 0 or less means there is no limit. */
  limit: number;
  premium: boolean;
  /** How many NFTs the user owns, including the ones past the limit. */
  total: number;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    v-if="!premium && limit > 0 && total > limit"
    type="info"
  >
    <PlanLimitMessage
      :label="t('plan_limit.labels.nfts')"
      :limit="limit"
      :total="total"
    />
  </RuiAlert>
</template>
