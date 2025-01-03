<script setup lang="ts">
import { useRefMap } from '@/composables/utils/useRefMap';
import { useDefiMetadata } from '@/composables/defi/metadata';
import DefiAsset from '@/components/defi/DefiAsset.vue';
import AppImage from '@/components/common/AppImage.vue';
import InfoRow from '@/components/defi/display/InfoRow.vue';
import StatCard from '@/components/display/StatCard.vue';
import type { DefiProtocolSummary } from '@/types/defi/overview';

const props = defineProps<{
  summary: DefiProtocolSummary;
}>();

const details = ref(false);
const { summary } = toRefs(props);
const { t } = useI18n();

const assets = computed(() => {
  const { assets } = get(summary);
  return assets.sort(({ balance: { usdValue } }, { balance: { usdValue: otherUsdValue } }) => {
    if (usdValue.eq(otherUsdValue))
      return 0;

    return usdValue.gt(otherUsdValue) ? -1 : 1;
  });
});

const { getDefiImage, getDefiName, loading } = useDefiMetadata();

const protocol = useRefMap(summary, i => i.protocol);
const name = getDefiName(protocol);
const imageUrl = getDefiImage(protocol);
</script>

<template>
  <StatCard
    v-if="!summary.balanceUsd"
    :title="name"
    :protocol-icon="imageUrl"
    bordered
    :loading="loading"
  >
    <div v-if="summary.liabilities">
      <div class="text-subtitle-1 font-bold pb-2 flex flex-row justify-between">
        {{ t('overview.stat_card.headers.borrowing') }}
        <RouterLink
          v-if="summary.liabilitiesUrl"
          :to="summary.liabilitiesUrl"
        >
          <RuiButton
            icon
            variant="text"
            size="sm"
            class="!p-2"
            color="primary"
          >
            <RuiIcon
              size="16"
              color="primary"
              name="lu-external-link"
            />
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
      <div class="pb-2 flex flex-row justify-between text-subtitle-1 font-medium">
        {{ t('common.deposits') }}
        <RouterLink
          v-if="summary.depositsUrl"
          :to="summary.depositsUrl"
        >
          <RuiButton
            icon
            variant="text"
            size="sm"
            class="!p-2"
            color="primary"
          >
            <RuiIcon
              size="16"
              color="primary"
              name="lu-external-link"
            />
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
  <StatCard
    v-else
    bordered
    :title="name"
    :protocol-icon="imageUrl"
    :loading="loading"
  >
    <span
      v-if="summary.tokenInfo"
      class="text-subtitle-1 font-bold pb-2"
    >
      {{ summary.tokenInfo.tokenName }}
    </span>
    <InfoRow
      :title="t('common.balance')"
      fiat
      :value="summary.balanceUsd"
    />

    <RuiDivider class="my-4" />

    <div class="flex justify-end">
      <RuiDialog
        v-model="details"
        max-width="450px"
      >
        <template #activator="{ attrs }">
          <RuiButton
            size="sm"
            variant="text"
            color="primary"
            v-bind="attrs"
          >
            {{ t('common.details') }}
            <template #append>
              <RuiIcon
                size="16"
                color="primary"
                name="lu-external-link"
              />
            </template>
          </RuiButton>
        </template>
        <RuiCard
          divide
          content-class="h-[300px] flex flex-col gap-2"
        >
          <template #custom-header>
            <div class="flex items-center p-4 gap-4">
              <AppImage
                :loading="loading"
                :src="imageUrl"
                size="32px"
                contain
              />

              <RuiCardHeader class="p-0">
                <template #header>
                  {{ name }}
                </template>
                <template #subheader>
                  {{ t('overview.details_dialog.subtitle') }}
                </template>
              </RuiCardHeader>
            </div>
          </template>
          <DefiAsset
            v-for="(asset, index) in assets"
            :key="index"
            :asset="asset"
          />
        </RuiCard>
      </RuiDialog>
    </div>
  </StatCard>
</template>
