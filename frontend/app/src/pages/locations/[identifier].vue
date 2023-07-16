<script setup lang="ts">
defineOptions({
  name: 'LocationBreakdown'
});

const props = defineProps<{
  identifier: string;
}>();

const { identifier } = toRefs(props);
const { locationData } = useLocations();
const location = locationData(identifier);
</script>

<template>
  <VContainer class="pb-12">
    <VRow align="center" class="mt-12">
      <VCol cols="auto">
        <LocationIcon
          v-if="location"
          :item="location"
          icon
          size="48px"
          no-padding
        />
      </VCol>
      <VCol class="d-flex flex-column" cols="auto">
        <span v-if="location" class="text-h5 font-weight-medium">
          {{ location.name }}
        </span>
      </VCol>
    </VRow>
    <LocationValueRow class="mt-8" :identifier="identifier" />
    <LocationAssets class="mt-8" :identifier="identifier" />
    <ClosedTrades :location-overview="identifier" />
    <DepositsWithdrawalsContent :location-overview="identifier" />
    <LedgerActionContent :location-overview="identifier" />
  </VContainer>
</template>
