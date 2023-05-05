<script setup lang="ts">
import { PremiumStatistics } from '@/premium/premium';

const premium = usePremium();
const { tc } = useI18n();
</script>

<template>
  <v-container>
    <no-premium-placeholder
      v-if="!premium"
      :text="tc('statistics.no_premium_label')"
    />
    <premium-statistics v-else />
  </v-container>
</template>
