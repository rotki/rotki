<template>
  <v-container>
    <no-premium-placeholder
      v-if="!premium"
      :text="$t('statistics.no_premium_label')"
    />
    <premium-statistics v-else :service="$api" :floating-precision="0" />
  </v-container>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import { getPremium } from '@/composables/session';
import { PremiumStatistics } from '@/premium/premium';

export default defineComponent({
  name: 'Statistics',
  components: { NoPremiumPlaceholder, PremiumStatistics },
  setup() {
    const premium = getPremium();
    return {
      premium
    };
  }
});
</script>
