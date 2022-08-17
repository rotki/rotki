<template>
  <v-container>
    <no-premium-placeholder
      v-if="!premium"
      :text="tc('statistics.no_premium_label')"
    />
    <premium-statistics v-else />
  </v-container>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { useI18n } from 'vue-i18n-composable';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import { getPremium } from '@/composables/session';
import { PremiumStatistics } from '@/premium/premium';

export default defineComponent({
  name: 'Statistics',
  components: { NoPremiumPlaceholder, PremiumStatistics },
  setup() {
    const premium = getPremium();
    const { tc } = useI18n();
    return {
      premium,
      tc
    };
  }
});
</script>
