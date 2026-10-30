<script setup lang="ts">
import type { InteractionConnection, InteractionNode } from './address-interaction-graph';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { counterpartOf, useNamedChain } from './address-interaction-panel';

/**
 * Rows of related address pairs. With a focused address each row names only the counterpart, since
 * the focused address is already stated above the list.
 */
const { connections, focusNodeId, connectionLabel } = defineProps<{
  connections: readonly InteractionConnection[];
  focusNodeId?: string;
  connectionLabel: (connection: InteractionConnection) => string;
}>();

const emit = defineEmits<{
  select: [connection: InteractionConnection];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();
const namedChain = useNamedChain();

const rows = computed<{ connection: InteractionConnection; counterpart?: InteractionNode }[]>(() =>
  connections.map(connection => ({ connection, counterpart: counterpartOf(connection, focusNodeId) })));
</script>

<template>
  <ul
    class="flex flex-col gap-1"
    data-testid="interaction-connection-list"
  >
    <li
      v-for="{ connection, counterpart } in rows"
      :key="connection.id"
    >
      <button
        type="button"
        class="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors hover:bg-rui-grey-100 focus-visible:outline-2 focus-visible:outline-rui-primary dark:hover:bg-rui-grey-800"
        :aria-label="connectionLabel(connection)"
        data-testid="interaction-connection"
        @click="emit('select', connection)"
      >
        <LocationIcon
          :item="connection.chain"
          :title="getChainName(connection.chain)"
          icon
          size="20px"
          class="shrink-0"
        />
        <div class="flex min-w-0 flex-1 flex-col">
          <HashLink
            v-if="counterpart"
            :text="counterpart.address"
            :location="namedChain(counterpart.address, counterpart.chains)"
            display-mode="text"
          />
          <template v-else>
            <HashLink
              :text="connection.source.address"
              :location="namedChain(connection.source.address, connection.source.chains)"
              display-mode="text"
            />
            <div class="flex min-w-0 items-center gap-1">
              <RuiIcon
                name="lu-arrow-left-right"
                size="12"
                class="shrink-0 text-rui-text-secondary"
                aria-hidden="true"
              />
              <HashLink
                :text="connection.target.address"
                :location="namedChain(connection.target.address, connection.target.chains)"
                display-mode="text"
              />
            </div>
          </template>
        </div>
        <span
          class="shrink-0 rounded-full bg-rui-grey-100 px-2 py-0.5 text-xs font-medium text-rui-text-secondary dark:bg-rui-grey-800"
          data-testid="interaction-connection-count"
        >
          {{ t('address_interactions.tx_count', { count: connection.txHashes.length }, connection.txHashes.length) }}
        </span>
      </button>
    </li>
  </ul>
</template>
