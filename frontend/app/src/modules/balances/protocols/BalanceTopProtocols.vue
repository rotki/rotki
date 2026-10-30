<script lang="ts" setup>
import type { ProtocolBalance } from '@rotki/common';
import ClaimAwaitingBadge from '@/modules/balances/protocols/components/ClaimAwaitingBadge.vue';
import ProtocolMenuItem from '@/modules/balances/protocols/ProtocolMenuItem.vue';
import ProtocolTooltipIcon from '@/modules/balances/protocols/ProtocolTooltipIcon.vue';
import { hasAwaitingClaim } from '@/modules/core/common/display/balances';

const { protocols, visible = 3 } = defineProps<{
  protocols: ProtocolBalance[];
  asset?: string;
  loading?: boolean;
  visible?: number;
}>();

const showMore = computed<number>(() => protocols.length - visible);
const claimable = computed<ProtocolBalance[]>(() => protocols.filter(hasAwaitingClaim));
</script>

<template>
  <div
    v-if="protocols.length > 0"
    class="flex items-center justify-end gap-1 pl-2"
  >
    <ClaimAwaitingBadge
      v-for="protocolBalance in claimable"
      :key="protocolBalance.protocol"
      :protocol-balance="protocolBalance"
      :asset="asset"
      compact
    />
    <ProtocolTooltipIcon
      v-if="protocols.length === 1"
      :protocol-balance="protocols[0]"
      :asset="asset"
      :loading="loading"
    />

    <template v-else>
      <ProtocolTooltipIcon
        v-for="protocolBalance in protocols.slice(0, visible)"
        :key="protocolBalance.protocol"
        :protocol-balance="protocolBalance"
        :asset="asset"
        :loading="loading"
      />

      <RuiMenu
        v-if="showMore > 0"
        open-on-hover
        lazy
        :close-delay="200"
        :options="{ placement: 'bottom' }"
      >
        <template #activator="{ open, attrs }">
          <div
            class="rounded-full h-7 px-1.5 min-w-7 bg-rui-grey-100 dark:bg-rui-grey-800 flex items-center justify-center font-medium text-xs text-rui-text-secondary cursor-pointer transition-colors"
            :class="{ 'bg-rui-grey-200 dark:bg-rui-grey-700': open }"
            v-bind="attrs"
          >
            {{ showMore }}+
          </div>
        </template>
        <div class="p-2 px-3 flex flex-col gap-1">
          <ProtocolMenuItem
            v-for="protocolBalance in protocols.slice(visible)"
            :key="protocolBalance.protocol"
            :protocol-balance="protocolBalance"
            :asset="asset"
            :loading="loading"
          />
        </div>
      </RuiMenu>
    </template>
  </div>
</template>
