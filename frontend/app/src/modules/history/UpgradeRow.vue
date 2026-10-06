<script setup lang="ts">
import PlanLimitMessage from '@/modules/premium/PlanLimitMessage.vue';

defineProps<{
  colspan: number;
  label: string;
  /** How many entries are shown, i.e. the premium limit. */
  limit: number;
  /** How many entries exist in total. */
  total: number;
  /** The processed time range of a report, see `PlanLimitMessage`. */
  range?: { timeStart: number; timeEnd: number };
}>();
</script>

<template>
  <tr class="bg-transparent">
    <td
      :colspan="colspan"
      class="font-medium py-2"
    >
      <PlanLimitMessage
        :label="label"
        :limit="limit"
        :total="total"
        :range="range"
        tag="div"
        class="md:text-center"
      />
    </td>
  </tr>
</template>
