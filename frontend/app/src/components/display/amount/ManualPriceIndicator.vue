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
  <div v-if="isManualPrice" class="mr-2 d-inline-block">
    <VTooltip bottom>
      <template #activator="{ on }">
        <VIcon class="mr-1" small color="warning" v-on="on">
          mdi-auto-fix
        </VIcon>
      </template>
      <span>{{ t('amount_display.manual_tooltip') }}</span>
    </VTooltip>
  </div>
</template>
