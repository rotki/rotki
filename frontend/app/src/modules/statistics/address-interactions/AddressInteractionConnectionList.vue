<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useScramble } from '@/modules/settings/use-scramble';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import { type InteractionConnection, type InteractionNode, transactionsOn } from './address-interaction-graph';
import { counterpartOf, PAGE_SIZE, usePagedList } from './address-interaction-panel';
import AddressInteractionPair from './AddressInteractionPair.vue';
import { useInteractionLabels } from './use-interaction-labels';

const limit = defineModel<number>('limit', { default: PAGE_SIZE });

/**
 * Compact rows of related address pairs. With a focused address each row names only the
 * counterpart, since the focused address is already stated above the list.
 *
 * @remarks
 * Only the first `limit` rows render, since a busy graph has hundreds of connections. The limit is a
 * model so the panel can keep it while this list is unmounted behind a connection's details. With a
 * `chain` filter, each row counts and shows only that chain. Copying an address or opening it in an
 * explorer happens in the pair's details, so a row is a single target.
 */
const { connections, focusNodeId, chain } = defineProps<{
  connections: readonly InteractionConnection[];
  focusNodeId?: string;
  chain?: string;
}>();

const emit = defineEmits<{
  select: [connection: InteractionConnection];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();
const { scrambleAddress } = useScramble();
const { connectionLabel } = useInteractionLabels();
const { nextCount, showMore, shown } = usePagedList(() => connections, limit);

interface ConnectionRow {
  connection: InteractionConnection;
  /** The addresses the row names, with their avatars: the counterpart alone, or both ends. */
  nodes: InteractionNode[];
  chains: string[];
  count: number;
}

const rows = computed<ConnectionRow[]>(() => get(shown).map((connection) => {
  const counterpart = counterpartOf(connection, focusNodeId);
  return {
    nodes: counterpart ? [counterpart] : [connection.source, connection.target],
    chains: chain ? [chain] : connection.activity.map(entry => entry.chain),
    connection,
    count: transactionsOn(connection, chain),
  };
}));
</script>

<template>
  <ul
    class="flex flex-col pl-0"
    data-testid="interaction-connection-list"
  >
    <li
      v-for="row in rows"
      :key="row.connection.id"
    >
      <button
        type="button"
        class="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-rui-grey-100 focus-visible:outline-2 focus-visible:outline-rui-primary dark:hover:bg-rui-grey-800"
        :aria-label="connectionLabel(row.connection)"
        data-testid="interaction-connection"
        @click="emit('select', row.connection)"
      >
        <span
          class="flex shrink-0"
          aria-hidden="true"
        >
          <span
            v-for="(node, index) in row.nodes"
            :key="node.id"
            class="flex rounded-full ring-2 ring-rui-surface"
            :class="{ '-ml-2': index > 0 }"
          >
            <EnsAvatar
              :address="scrambleAddress(node.address)"
              size="20px"
              avatar
            />
          </span>
        </span>
        <span class="flex min-w-0 flex-1 flex-col">
          <AddressInteractionPair
            :nodes="row.nodes"
            class="text-sm"
            data-testid="interaction-connection-label"
          />
          <span class="flex items-center gap-1 text-xs text-rui-text-secondary">
            <span
              class="flex items-center gap-1"
              data-testid="interaction-connection-chains"
            >
              <LocationIcon
                v-for="item in row.chains"
                :key="item"
                :item="item"
                :title="getChainName(item)"
                icon
                size="12px"
              />
            </span>
            <span
              class="size-0.5 rounded-full bg-current"
              aria-hidden="true"
            />
            <span data-testid="interaction-connection-count">
              {{ t('address_interactions.tx_count', { count: row.count }, row.count) }}
            </span>
          </span>
        </span>
      </button>
    </li>
    <li v-if="nextCount > 0">
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        class="w-full"
        data-testid="interaction-connection-show-more"
        @click="showMore()"
      >
        {{ t('address_interactions.show_more', { count: nextCount }) }}
      </RuiButton>
    </li>
  </ul>
</template>
