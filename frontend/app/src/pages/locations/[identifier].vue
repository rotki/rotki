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
    <div v-if="location" class="flex flex-row items-center my-4 gap-2">
      <LocationIcon :item="identifier" icon size="48px" />
      <span class="text-h5 font-medium">
        {{ location.name }}
      </span>
    </div>
    <LocationValueRow :identifier="identifier" />
    <LocationAssets :identifier="identifier" />
    <ClosedTrades :location-overview="identifier" />
    <DepositsWithdrawalsContent :location-overview="identifier" />
  </div>
</template>
