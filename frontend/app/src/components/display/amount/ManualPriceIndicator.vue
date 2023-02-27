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
    <v-tooltip bottom>
      <template #activator="{ on }">
        <v-icon class="mr-1" small color="warning" v-on="on">
          mdi-auto-fix
        </v-icon>
      </template>
      <span>{{ t('amount_display.manual_tooltip') }}</span>
    </v-tooltip>
  </div>
</template>
