<script setup lang="ts">
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
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
</script>

<template>
  <div class="flex items-center gap-2">
    <div class="w-6">
      <RpcReconnectButton
        v-if="status === NODE_STATUS.FAILED && active"
        :disabled="reconnecting"
        :tooltip="t('evm_rpc_node_manager.reconnect.single')"
        @reconnect="emit('reconnect')"
      />
    </div>
    <BadgeDisplay
      v-if="status === NODE_STATUS.CONNECTED"
      color="green"
      class="items-center gap-2 !leading-6"
    >
      <RuiIcon
        color="success"
        size="16"
        name="lu-wifi"
      />
      <span>
        {{ t('evm_rpc_node_manager.connected.true') }}
      </span>
    </BadgeDisplay>
    <RuiTooltip
      v-else-if="status === NODE_STATUS.COOLING_DOWN"
      :open-delay="400"
    >
      <template #activator>
        <BadgeDisplay
          color="orange"
          class="items-center gap-2 !leading-6"
        >
          <RuiIcon
            size="16"
            name="lu-clock"
          />
          <span>
            {{ t('evm_rpc_node_manager.connected.cooling_down') }}
          </span>
        </BadgeDisplay>
      </template>
      <span v-if="cooldownUntil">
        {{ t('evm_rpc_node_manager.cooldown_until') }}
        <DateDisplay :timestamp="cooldownUntil" />
      </span>
    </RuiTooltip>
    <BadgeDisplay
      v-else-if="status === NODE_STATUS.FAILED"
      color="red"
      class="items-center gap-2 !leading-6"
    >
      <RuiIcon
        color="error"
        size="16"
        name="lu-wifi-off"
      />
      <span>
        {{ t('evm_rpc_node_manager.connected.failure') }}
      </span>
    </BadgeDisplay>
    <BadgeDisplay
      v-else
      color="grey"
      class="items-center gap-2 !leading-6"
    >
      <RuiIcon
        color="info"
        size="16"
        name="lu-wifi"
      />
      <span>
        {{ t('evm_rpc_node_manager.connected.false') }}
      </span>
    </BadgeDisplay>
  </div>
</template>
