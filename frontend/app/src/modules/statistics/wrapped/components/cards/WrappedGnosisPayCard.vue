<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { getPublicServiceImagePath } from '@/utils/file';
import { useWrappedFormatters } from '../../composables/use-wrapped-formatters';
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
  >
    <template #header-icon>
      <AppImage
        :src="getPublicServiceImagePath('gnosispay.png')"
        width="24px"
        height="24px"
        contain
      />
    </template>
    <template #header>
      {{ t('wrapped.gnosis_payments') }}
    </template>
    <template #label="{ item }">
      <div
        class="flex items-center justify-center gap-2 size-6 rounded-full bg-rui-grey-300 dark:bg-rui-grey-800"
        :style="{ fontSize: calculateFontSize(item.symbol) }"
      >
        {{ item.symbol }}
      </div>
      <div>
        {{ item.code }} - {{ item.name }}
      </div>
    </template>
    <template #value="{ item }">
      <AmountDisplay
        force-currency
        :value="item.amount"
      />
      {{ item.symbol }}
    </template>
  </WrappedCard>
</template>
