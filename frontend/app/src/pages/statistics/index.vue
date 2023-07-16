<script setup lang="ts">
import { PremiumStatistics } from '@/premium/premium';

const premium = usePremium();
const { t } = useI18n();
</script>

<template>
  <VContainer>
    <NoPremiumPlaceholder
      v-if="!premium"
      :text="t('statistics.no_premium_label')"
    />
    <PremiumStatistics v-else />
  </VContainer>
</template>
