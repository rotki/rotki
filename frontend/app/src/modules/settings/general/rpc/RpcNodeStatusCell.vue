<script setup lang="ts">
import { NODE_STATUS, type NodeStatus } from '@/modules/settings/general/rpc/rpc-node-status';
import RpcReconnectButton from '@/modules/settings/general/rpc/RpcReconnectButton.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { status, active = false, cooldownUntil, reconnecting = false } = defineProps<{
  status: NodeStatus;
  active?: boolean;
  cooldownUntil?: number | null;
  reconnecting?: boolean;
}>();

const emit = defineEmits<{
  reconnect: [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** A dot colour and a label per status, read at a glance instead of a filled badge per row. */
const display = computed<{ dot: string; label: string }>(() => {
  switch (status) {
    case NODE_STATUS.CONNECTED:
      return { dot: 'bg-rui-success', label: t('evm_rpc_node_manager.connected.true') };
    case NODE_STATUS.COOLING_DOWN:
      return { dot: 'bg-rui-warning', label: t('evm_rpc_node_manager.connected.cooling_down') };
    case NODE_STATUS.FAILED:
      return { dot: 'bg-rui-error', label: t('evm_rpc_node_manager.connected.failure') };
    default:
      return { dot: 'bg-rui-grey-400', label: t('evm_rpc_node_manager.connected.false') };
  }
});
</script>

<template>
  <div class="flex items-center gap-2">
    <RuiTooltip
      :disabled="status !== NODE_STATUS.COOLING_DOWN || !cooldownUntil"
      :open-delay="400"
    >
      <template #activator>
        <span class="inline-flex items-center gap-1.5 text-sm text-rui-text whitespace-nowrap">
          <span
            class="size-2 shrink-0 rounded-full"
            :class="display.dot"
          />
          {{ display.label }}
        </span>
      </template>
      <span v-if="cooldownUntil">
        {{ t('evm_rpc_node_manager.cooldown_until') }}
        <DateDisplay :timestamp="cooldownUntil" />
      </span>
    </RuiTooltip>
    <RpcReconnectButton
      v-if="status === NODE_STATUS.FAILED && active"
      :disabled="reconnecting"
      :tooltip="t('evm_rpc_node_manager.reconnect.single')"
      @reconnect="emit('reconnect')"
    />
  </div>
</template>
