<template>
  <v-container>
    <report-header :period="report" />
    <card v-if="showUpgradeMessage" class="mt-4 mb-8">
      <i18n tag="div" path="profit_loss_report.upgrade" class="text-subtitle-1">
        <template #processed>
          <span class="font-weight-medium">{{ report.entriesFound }}</span>
        </template>
        <template #start>
          <date-display
            :timestamp="report.firstProcessedTimestamp"
            class="font-weight-medium"
            no-timezone
          />
        </template>
      </i18n>
      <i18n tag="div" path="profit_loss_report.upgrade2">
        <template #link>
          <base-external-link
            :text="$t('upgrade_row.rotki_premium')"
            :href="$interop.premiumURL"
          />
        </template>
      </i18n>
    </card>
    <accounting-settings-display
      :accounting-settings="accountingSettings"
      class="mt-4"
    />
    <profit-loss-overview
      class="mt-8"
      :overview="report.overview"
      :loading="loading"
    />
    <profit-loss-events class="mt-8" />
  </v-container>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  ref
} from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import AccountingSettingsDisplay from '@/components/profitloss/AccountingSettingsDisplay.vue';
import ProfitLossEvents from '@/components/profitloss/ProfitLossEvents.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import ReportHeader from '@/components/profitloss/ReportHeader.vue';
import { useRoute } from '@/composables/common';
import { useReports } from '@/store/reports';

export default defineComponent({
  name: 'ProfitLossReports',
  components: {
    ReportHeader,
    BaseExternalLink,
    ProfitLossOverview,
    ProfitLossEvents,
    AccountingSettingsDisplay
  },
  setup() {
    const loading = ref(true);
    const reportsStore = useReports();
    const { report } = storeToRefs(reportsStore);
    const { fetchReport } = reportsStore;
    const route = useRoute();

    onMounted(async () => {
      const currentRoute = route.value;
      await fetchReport(parseInt(currentRoute.params.id));
      loading.value = false;
    });

    const showUpgradeMessage = computed(
      () =>
        report.value.entriesLimit > 0 &&
        report.value.entriesLimit < report.value.entriesFound
    );

    return {
      loading,
      report,
      showUpgradeMessage
    };
  }
});
</script>
