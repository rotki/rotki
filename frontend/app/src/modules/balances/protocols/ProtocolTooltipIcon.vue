<script lang="ts" setup>
import { type ProtocolBalance, toSentenceCase } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import ProtocolIcon from '@/modules/balances/protocols/ProtocolIcon.vue';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const props = defineProps<{
  protocolBalance: ProtocolBalance;
  asset?: string;
  loading?: boolean;
}>();

const { protocolBalance } = toRefs(props);
const protocol = useRefMap(protocolBalance, balance => balance.protocol);

const { shouldShowAmount } = storeToRefs(useFrontendSettingsStore());
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
      <ProtocolIcon
        :protocol="protocol"
        :size="20"
        :loading="loading"
      />
    </template>

    <div class="flex flex-col gap-0.5">
      <div class="font-medium text-sm mb-0.5">
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
