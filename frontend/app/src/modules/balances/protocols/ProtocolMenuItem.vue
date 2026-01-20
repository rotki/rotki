<script lang="ts" setup>
import { type ProtocolBalance, toSentenceCase, toSnakeCase } from '@rotki/common';
import { useRefMap } from '@/composables/utils/useRefMap';
import { AssetAmountDisplay, FiatDisplay, ValueDisplay } from '@/modules/amount-display/components';
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
        <AssetAmountDisplay
          v-if="asset"
          :asset="asset"
          :amount="protocolBalance.amount"
          :loading="loading"
          data-cy="protocol-menu-amount"
        />
        <ValueDisplay
          v-else
          :value="protocolBalance.amount"
          :loading="loading"
          data-cy="protocol-menu-amount"
        />
        <span class="text-rui-text-secondary">
          {{ dot }}
        </span>
        <FiatDisplay
          :value="protocolBalance.value"
          :loading="loading"
          data-cy="protocol-menu-value"
        />
      </div>
    </div>
  </div>
</template>
