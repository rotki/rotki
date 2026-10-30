<script setup lang="ts">
import type { InteractionConnection } from './address-interaction-graph';
import { startPromise } from '@shared/utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { historyEventsRoute } from './address-interaction-panel';

const { connection } = defineProps<{ connection: InteractionConnection }>();

const emit = defineEmits<{
  back: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const { getChainName } = useSupportedChains();

function openInHistory(txHashes: readonly string[]): void {
  startPromise(router.push(historyEventsRoute(txHashes)));
}
</script>

<template>
  <div
    aria-live="polite"
    class="flex min-w-0 flex-col"
    data-testid="interaction-details"
  >
    <div class="flex flex-col gap-3 border-b border-default p-4 pt-2">
      <RuiButton
        variant="text"
        size="sm"
        class="-ml-2 self-start"
        data-testid="interaction-details-back"
        @click="emit('back')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-arrow-left"
            size="14"
          />
        </template>
        {{ t('common.actions.back') }}
      </RuiButton>
      <h3 class="text-base font-semibold">
        {{ t('address_interactions.selected_connection') }}
      </h3>
      <div class="flex flex-col">
        <HashLink
          :text="connection.source.address"
          :location="connection.chain"
          :size="14"
        />
        <div class="flex items-center gap-2 py-1 pl-1 text-xs text-rui-text-secondary">
          <RuiIcon
            name="lu-arrow-up-down"
            size="14"
            aria-hidden="true"
          />
          <LocationIcon
            :item="connection.chain"
            icon
            size="16px"
          />
          <span>
            {{ t('address_interactions.connection_summary', { chain: getChainName(connection.chain), count: connection.txHashes.length }, connection.txHashes.length) }}
          </span>
        </div>
        <HashLink
          :text="connection.target.address"
          :location="connection.chain"
          :size="14"
        />
      </div>
    </div>
    <section class="flex min-w-0 flex-col gap-2 p-4">
      <div class="flex items-center justify-between gap-2">
        <h4 class="text-xs font-medium text-rui-text-secondary">
          {{ t('address_interactions.transactions', { count: connection.txHashes.length }) }}
        </h4>
        <RuiButton
          variant="text"
          color="primary"
          size="sm"
          class="-mr-2"
          data-testid="interaction-history-link"
          @click="openInHistory(connection.txHashes)"
        >
          {{ t('address_interactions.view_in_history') }}
          <template #append>
            <RuiIcon
              name="lu-arrow-right"
              size="14"
            />
          </template>
        </RuiButton>
      </div>
      <ul class="flex min-w-0 flex-col divide-y divide-rui-grey-200 rounded-md border border-default dark:divide-rui-grey-800">
        <li
          v-for="hash in connection.txHashes"
          :key="hash"
          class="group/row flex min-w-0 items-center justify-between gap-2 py-1 pl-3 pr-1"
        >
          <HashLink
            :text="hash"
            :location="connection.chain"
            :truncate-length="8"
            :size="14"
            type="transaction"
            reveal-actions
          />
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="shrink-0"
            :aria-label="t('address_interactions.open_tx_in_history')"
            :title="t('address_interactions.open_tx_in_history')"
            data-testid="interaction-tx-history"
            @click="openInHistory([hash])"
          >
            <RuiIcon
              name="lu-history"
              size="16"
            />
          </RuiButton>
        </li>
      </ul>
    </section>
  </div>
</template>
