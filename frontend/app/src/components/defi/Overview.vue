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
  >
    <div v-if="summary.liabilities">
      <div class="text-subtitle-1 font-bold pb-2 flex flex-row justify-between">
        {{ t('overview.stat_card.headers.borrowing') }}
        <RouterLink v-if="summary.liabilitiesUrl" :to="summary.liabilitiesUrl">
          <RuiButton icon variant="text" size="sm" class="!p-2" color="primary">
            <RuiIcon size="16" color="primary" name="external-link-line" />
          </RuiButton>
        </RouterLink>
      </div>
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

      <RuiDivider class="my-4" />
    </div>
    <div v-if="summary.deposits">
      <div
        class="pb-2 flex flex-row justify-between text-subtitle-1 font-medium"
      >
        {{ t('common.deposits') }}
        <RouterLink v-if="summary.depositsUrl" :to="summary.depositsUrl">
          <RuiButton icon variant="text" size="sm" class="!p-2" color="primary">
            <RuiIcon size="16" color="primary" name="external-link-line" />
          </RuiButton>
        </RouterLink>
      </div>
      <InfoRow
        :title="t('overview.stat_card.content.labels.total_deposited')"
        fiat
        :value="summary.totalLendingDepositUsd"
      />
    </div>
  </StatCard>
  <StatCard v-else bordered :title="name" :protocol-icon="imageUrl">
    <span v-if="summary.tokenInfo" class="text-subtitle-1 font-bold pb-2">
      {{ summary.tokenInfo.tokenName }}
    </span>
    <InfoRow :title="t('common.balance')" fiat :value="summary.balanceUsd" />

    <RuiDivider class="my-4" />

    <div class="flex justify-end">
      <VDialog v-model="details" scrollable max-width="450px">
        <template #activator="{ on }">
          <RuiButton size="sm" variant="text" color="primary" v-on="on">
            {{ t('common.details') }}
            <template #append>
              <RuiIcon size="16" color="primary" name="external-link-line" />
            </template>
          </RuiButton>
        </template>
        <RuiCard>
          <template #custom-header>
            <div class="flex items-center p-4 gap-4">
              <AppImage
                :src="imageUrl"
                max-width="32px"
                max-height="32px"
                contain
              />
              <div>
                <div class="text-h5">{{ name }}</div>
                <div class="text-body-1 text-rui-text-secondary">
                  {{ t('overview.details_dialog.subtitle') }}
                </div>
              </div>
            </div>
          </template>
          <div class="h-[300px]">
            <div v-for="(asset, index) in assets" :key="index">
              <RuiDivider />
              <DefiAsset :asset="asset" />
            </div>
          </div>
        </RuiCard>
      </VDialog>
    </div>
  </StatCard>
</template>
