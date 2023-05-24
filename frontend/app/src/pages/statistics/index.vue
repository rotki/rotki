<script setup lang="ts">
import { PremiumStatistics } from '@/premium/premium';

const premium = usePremium();
const { t } = useI18n();
</script>

<template>
  <v-container>
    <no-premium-placeholder
      v-if="!premium"
      :text="t('statistics.no_premium_label')"
    />
    <premium-statistics v-else />
  </v-container>
</template>
