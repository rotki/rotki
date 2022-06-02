<template>
  <div class="wrapper">
    <report-actionable initial-open />
  </div>
</template>
<script setup lang="ts">
import { onBeforeMount } from '@vue/composition-api';
import ReportActionable from '@/components/profitloss/ReportActionable.vue';
import { useReports } from '@/store/reports';

const { fetchActionableItems } = useReports();

onBeforeMount(() => {
  fetchActionableItems();
});
</script>
<style scoped lang="scss">
::v-deep {
  body {
    overflow: visible !important;
  }
}

.wrapper {
  margin-top: -64px;
}
</style>
