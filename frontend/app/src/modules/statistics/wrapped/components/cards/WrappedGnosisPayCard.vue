<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import AppImage from '@/modules/shell/components/AppImage.vue';
import { useWrappedFormatters } from '../../use-wrapped-formatters';
import WrappedCard from '../WrappedCard.vue';

interface GnosisPayResult {
  amount: BigNumber;
  code: string;
  name: string;
  symbol: string;
}

defineProps<{
  gnosisPayResult: GnosisPayResult[];
  showGnosisData: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { calculateFontSize } = useWrappedFormatters();
</script>

<template>
  <WrappedCard
    v-if="showGnosisData && gnosisPayResult.length > 0"
    :items="gnosisPayResult"
    :ranked="false"
  >
    <template #header-icon>
      <AppImage
        :src="getPublicServiceImagePath('gnosispay.png')"
        width="16px"
        height="16px"
        fit="contain"
      />
    </template>
    <template #header>
      {{ t('wrapped.gnosis_payments') }}
    </template>
    <template #label="{ item }">
      <span
        class="flex items-center justify-center size-6 shrink-0 rounded-full bg-rui-grey-200 dark:bg-rui-grey-800 font-medium"
        :style="{ fontSize: calculateFontSize(item.symbol) }"
      >
        {{ item.symbol }}
      </span>
      <span class="truncate">{{ item.code }} - {{ item.name }}</span>
    </template>
    <template #value="{ item }">
      <FiatDisplay
        :value="item.amount"
        :currency="item.code"
        symbol="none"
      />
      <span class="font-normal text-rui-text-secondary">{{ item.symbol }}</span>
    </template>
  </WrappedCard>
</template>
