<script setup lang="ts">
import { type TradeLocationData } from '@/types/history/trade/location';

defineOptions({
  name: 'LocationBreakdown'
});

const props = defineProps<{
  identifier: string;
}>();

const { identifier } = toRefs(props);

const { getLocation } = useLocations();

const location: ComputedRef<TradeLocationData> = computed(() =>
  getLocation(identifier)
);
</script>
<template>
  <v-container class="pb-12">
    <v-row align="center" class="mt-12">
      <v-col cols="auto">
        <location-icon :item="location" icon size="48px" no-padding />
      </v-col>
      <v-col class="d-flex flex-column" cols="auto">
        <span class="text-h5 font-weight-medium">{{ location.name }}</span>
      </v-col>
    </v-row>
    <location-value-row class="mt-8" :identifier="identifier" />
    <location-assets class="mt-8" :identifier="identifier" />
    <closed-trades :location-overview="identifier" />
    <deposits-withdrawals-content :location-overview="identifier" />
    <ledger-action-content :location-overview="identifier" />
  </v-container>
</template>
