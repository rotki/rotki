<script lang="ts" setup>
import type { ProtocolBalance } from '@rotki/common';
import ProtocolIcon from '@/modules/balances/protocols/ProtocolIcon.vue';

const props = withDefaults(defineProps<{
  protocols: ProtocolBalance[];
  asset?: string;
  loading?: boolean;
  visible?: number;
}>(), {
  loading: false,
  visible: 3,
});

const { protocols, visible } = toRefs(props);

const showMore = computed<number>(() => get(protocols).length - get(visible));
</script>

<template>
  <div
    v-if="protocols.length > 0"
    class="flex justify-end pl-2"
  >
    <!-- Single protocol: no tooltip, no overlap -->
    <ProtocolIcon
      v-if="protocols.length === 1"
      :protocol-balance="protocols[0]"
      :asset="asset"
      :loading="loading"
    />

    <!-- Multiple protocols: with tooltips and overlap -->
    <template v-else>
      <ProtocolIcon
        v-for="protocolBalance in protocols.slice(0, visible)"
        :key="protocolBalance.protocol"
        :protocol-balance="protocolBalance"
        :asset="asset"
        :loading="loading"
        class="-ml-2"
      />

      <div
        v-if="showMore > 0"
        class="rounded-full h-8 px-1 min-w-8 bg-rui-grey-300 dark:bg-white flex items-center justify-center border-2 border-white dark:border-rui-grey-300 -ml-2 font-bold text-xs text-rui-light-text z-[1]"
      >
        {{ showMore }}+
      </div>
    </template>
  </div>
</template>
