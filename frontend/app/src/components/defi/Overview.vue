<script setup lang="ts">
import { type DefiProtocolSummary } from '@/types/defi/overview';

const props = defineProps<{
  summary: DefiProtocolSummary;
}>();

const details = ref(false);
const { summary } = toRefs(props);
const { t } = useI18n();

const assets = computed(() => {
  const { assets } = get(summary);
  return assets.sort(
    ({ balance: { usdValue } }, { balance: { usdValue: otherUsdValue } }) => {
      if (usdValue.eq(otherUsdValue)) {
        return 0;
      }
      return usdValue.gt(otherUsdValue) ? -1 : 1;
    }
  );
});

const css = useCssModule();

const { getDefiName, getDefiImage } = useDefiMetadata();

const protocol = useRefMap(summary, i => i.protocol);
const reactiveDecoder = reactify(decodeHtmlEntities);

const name = reactiveDecoder(getDefiName(protocol));
const image = getDefiImage(protocol);

const imageUrl = computed(() => {
  const imageVal = get(image);
  if (!imageVal) {
    return '';
  }
  return `./assets/images/protocols/${imageVal}`;
});
</script>

<template>
  <StatCard
    v-if="!summary.balanceUsd"
    :title="name"
    :protocol-icon="imageUrl"
    bordered
    :class="css.overview"
  >
    <div v-if="summary.liabilities">
      <span
        class="text-subtitle-1 font-bold pb-2 flex flex-row justify-between"
      >
        {{ t('overview.stat_card.headers.borrowing') }}
        <VBtn :to="summary.liabilitiesUrl" icon small color="primary">
          <VIcon small color="primary">mdi-launch</VIcon>
        </VBtn>
      </span>
      <InfoRow
        :title="t('overview.stat_card.content.labels.total_collateral')"
        fiat
        :value="summary.totalCollateralUsd"
      />
      <InfoRow
        :title="t('overview.stat_card.content.labels.total_debt')"
        fiat
        :value="summary.totalDebtUsd"
      />
      <VDivider class="my-4" />
    </div>
    <div v-if="summary.deposits">
      <div
        class="pb-2 flex flex-row justify-between text-subtitle-1 font-medium"
      >
        {{ t('common.deposits') }}
        <VBtn
          v-if="summary.depositsUrl"
          :to="summary.depositsUrl"
          icon
          small
          color="primary"
        >
          <VIcon small color="primary">mdi-launch</VIcon>
        </VBtn>
      </div>
      <InfoRow
        :title="t('overview.stat_card.content.labels.total_deposited')"
        fiat
        :value="summary.totalLendingDepositUsd"
      />
    </div>
  </StatCard>
  <StatCard
    v-else
    bordered
    :title="name"
    :protocol-icon="imageUrl"
    :class="css.overview"
  >
    <span v-if="summary.tokenInfo" class="text-subtitle-1 font-bold pb-2">
      {{ summary.tokenInfo.tokenName }}
    </span>
    <InfoRow :title="t('common.balance')" fiat :value="summary.balanceUsd" />
    <VDivider class="my-4" />
    <div class="flex justify-end">
      <VDialog v-model="details" scrollable max-width="450px">
        <template #activator="{ on, attrs }">
          <VBtn small v-bind="attrs" text class="justify-end" v-on="on">
            {{ t('common.details') }}
            <VIcon color="primary" right>mdi-launch</VIcon>
          </VBtn>
        </template>
        <VCard>
          <VCardTitle class="mb-2">
            <VImg
              aspect-ratio="1"
              :src="imageUrl"
              max-width="32px"
              max-height="32px"
              contain
            />
            <span class="ml-2">
              {{ name }}
            </span>
          </VCardTitle>
          <VCardSubtitle>
            {{ t('overview.details_dialog.subtitle') }}
          </VCardSubtitle>
          <VCardText :class="css.details">
            <div v-for="(asset, index) in assets" :key="index">
              <DefiAsset :asset="asset" />
              <VDivider />
            </div>
          </VCardText>
        </VCard>
      </VDialog>
    </div>
  </StatCard>
</template>

<style module lang="scss">
.overview {
  min-height: 250px !important;
  min-width: 300px;
}

.details {
  height: 300px;
}
</style>
