<script lang="ts" setup>
import { type ProtocolBalance, toSentenceCase, toSnakeCase } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import ProtocolIcon from '@/modules/balances/protocols/ProtocolIcon.vue';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';

const props = defineProps<{
  protocolBalance: ProtocolBalance;
  asset?: string;
  loading?: boolean;
}>();

const { protocolBalance } = toRefs(props);
const protocol = useRefMap(protocolBalance, balance => balance.protocol);

const { t } = useI18n({ useScope: 'global' });
const { protocolData } = useProtocolData(protocol);

const dot = '•';
</script>

<template>
  <div class="flex items-center gap-3 py-1">
    <ProtocolIcon
      :protocol="toSnakeCase(protocol)"
      :size="20"
      :loading="loading"
    />

    <div class="flex flex-col flex-1">
      <div class="font-medium text-sm">
        {{ protocolData?.name ?? toSentenceCase(protocol) }}
        <span
          v-if="protocolBalance.containsManual"
          class="font-normal text-caption text-rui-text-secondary"
        >
          {{ t('protocol_icon.contains_manual') }}
        </span>
      </div>

      <div class="flex items-center gap-2 text-caption">
        <AmountDisplay
          :value="protocolBalance.amount"
          :asset="asset"
          :asset-padding="0.1"
          data-cy="protocol-menu-amount"
        />
        <span class="text-rui-text-secondary">
          {{ dot }}
        </span>
        <AmountDisplay
          :asset-padding="0.1"
          fiat-currency="USD"
          :value="protocolBalance.usdValue"
          show-currency="symbol"
          data-cy="protocol-menu-value"
        />
      </div>
    </div>
  </div>
</template>
