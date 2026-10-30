<script setup lang="ts">
import type { InteractionConnection, InteractionNode } from './address-interaction-graph';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { CONNECTION_PAGE_SIZE, useNamedChain } from './address-interaction-panel';
import AddressInteractionConnectionList from './AddressInteractionConnectionList.vue';
import AddressInteractionDetails from './AddressInteractionDetails.vue';

/**
 * Side panel that follows the graph selection: every connection, then the connections of a selected
 * address, then the transactions of a selected connection.
 */
const { connections, selectedNode, selectedConnection, connectionLabel } = defineProps<{
  connections: readonly InteractionConnection[];
  selectedNode?: InteractionNode;
  selectedConnection?: InteractionConnection;
  connectionLabel: (connection: InteractionConnection) => string;
}>();

const emit = defineEmits<{
  'select-connection': [connection: InteractionConnection];
  'clear-connection': [];
  'clear-node': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const connectionLimit = shallowRef<number>(CONNECTION_PAGE_SIZE);

const namedChain = useNamedChain();

watch(() => connections, () => {
  set(connectionLimit, CONNECTION_PAGE_SIZE);
});
</script>

<template>
  <AddressInteractionDetails
    v-if="selectedConnection"
    :connection="selectedConnection"
    @back="emit('clear-connection')"
  />
  <div
    v-else
    class="flex min-w-0 flex-col"
  >
    <div
      v-if="selectedNode"
      class="flex flex-col gap-2 border-b border-default p-4"
      data-testid="interaction-panel-node"
    >
      <div class="flex items-center justify-between gap-2">
        <h3 class="text-xs font-medium text-rui-text-secondary">
          {{ t('address_interactions.selected_address') }}
        </h3>
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="-my-1 text-rui-text-secondary!"
          :aria-label="t('address_interactions.clear_selection')"
          data-testid="interaction-panel-clear-node"
          @click="emit('clear-node')"
        >
          <RuiIcon
            name="lu-x"
            size="16"
          />
        </RuiButton>
      </div>
      <HashLink
        :text="selectedNode.address"
        :location="namedChain(selectedNode.address, selectedNode.chains)"
        :size="14"
      />
      <div class="flex flex-wrap items-center gap-1">
        <LocationIcon
          v-for="chain in selectedNode.chains"
          :key="chain"
          :item="chain"
          icon
          size="16px"
        />
      </div>
    </div>
    <div class="flex flex-col gap-2 p-4">
      <div class="flex flex-col">
        <h3 class="text-sm font-semibold">
          {{ selectedNode
            ? t('address_interactions.connected_addresses', { count: connections.length })
            : t('address_interactions.connections', { count: connections.length }) }}
        </h3>
        <p class="text-xs text-rui-text-secondary">
          {{ t('address_interactions.sorted_by_activity') }}
        </p>
      </div>
      <AddressInteractionConnectionList
        v-model:limit="connectionLimit"
        :connections="connections"
        :focus-node-id="selectedNode?.id"
        :connection-label="connectionLabel"
        class="-mx-2"
        @select="emit('select-connection', $event)"
      />
    </div>
  </div>
</template>
