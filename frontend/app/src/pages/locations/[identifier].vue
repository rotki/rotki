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
  <div class="flex flex-col gap-4 mx-4">
    <div class="flex flex-row items-center my-4">
      <LocationIcon
        v-if="location"
        :item="location"
        icon
        size="48px"
        no-padding
      />
      <span v-if="location" class="text-h5 font-medium">
        {{ location.name }}
      </span>
    </div>
    <LocationValueRow :identifier="identifier" />
    <LocationAssets :identifier="identifier" />
    <ClosedTrades :location-overview="identifier" />
    <DepositsWithdrawalsContent :location-overview="identifier" />
    <LedgerActionContent :location-overview="identifier" />
  </div>
</template>
