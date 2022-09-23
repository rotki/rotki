<template>
  <v-container>
    <no-premium-placeholder
      v-if="!premium"
      :text="tc('statistics.no_premium_label')"
    />
    <premium-statistics v-else />
  </v-container>
</template>

<script setup lang="ts">
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import { usePremium } from '@/composables/premium';
import { PremiumStatistics } from '@/premium/premium';

const premium = usePremium();
const { tc } = useI18n();
</script>
