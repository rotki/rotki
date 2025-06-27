<script lang="ts" setup>
import AppImage from '@/components/common/AppImage.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import { useSessionSettingsStore } from '@/store/settings/session';
import { type ProtocolBalance, toSentenceCase } from '@rotki/common';

const props = defineProps<{
  protocolBalance: ProtocolBalance;
  asset?: string;
  loading?: boolean;
}>();

const { protocolBalance } = toRefs(props);
const protocol = useRefMap(protocolBalance, balance => balance.protocol);

const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());
const { t } = useI18n({ useScope: 'global' });
const { protocolData } = useProtocolData(protocol);
</script>

<template>
  <RuiTooltip
    :disabled="!shouldShowAmount"
    :close-delay="0"
    tooltip-class="!-ml-1"
  >
    <template #activator>
      <div
        data-cy="top-protocol"
        class="rounded-full size-8 flex items-center justify-center border bg-white border-rui-grey-300 dark:border-rui-grey-700 cursor-pointer"
      >
        <RuiIcon
          v-if="protocolData?.type === 'icon'"
          color="secondary"
          :size="20"
          :name="protocolData.icon"
        />
        <AppImage
          v-else-if="protocolData?.type === 'image'"
          class="icon-bg rounded-full overflow-hidden"
          :src="protocolData.image"
          size="24px"
          :loading="loading"
          contain
        />
        <RuiIcon
          v-else
          name="lu-blocks"
          color="secondary"
          :size="20"
        />
      </div>
    </template>

    <div class="flex flex-col gap-1">
      <div class="font-medium text-sm">
        {{ protocolData?.name ?? toSentenceCase(protocol) }}
        <div
          v-if="protocolBalance.containsManual"
          class="font-normal text-caption"
        >
          {{ t('protocol_icon.contains_manual') }}
        </div>
      </div>
      <AmountDisplay
        :value="protocolBalance.amount"
        :asset="asset"
        :asset-padding="0.1"
        data-cy="top-protocol-amount"
      />
      <AmountDisplay
        :asset-padding="0.1"
        fiat-currency="USD"
        :value="protocolBalance.usdValue"
        show-currency="symbol"
        data-cy="top-protocol-value"
      />
    </div>
  </RuiTooltip>
</template>
