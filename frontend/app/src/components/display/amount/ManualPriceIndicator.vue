<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    priceAsset?: string;
  }>(),
  {
    priceAsset: ''
  }
);

const { priceAsset } = toRefs(props);
const { t } = useI18n();
const { isManualAssetPrice } = useBalancePricesStore();

const isManualPrice = isManualAssetPrice(priceAsset);
</script>

<template>
  <RuiTooltip
    v-if="isManualPrice"
    :popper="{ placement: 'top' }"
    open-delay="400"
  >
    <template #activator>
      <RuiIcon
        class="mr-3 mb-1 inline cursor-pointer"
        size="16"
        color="warning"
        name="sparkling-line"
      />
    </template>
    <span>{{ t('amount_display.manual_tooltip') }}</span>
  </RuiTooltip>
</template>
