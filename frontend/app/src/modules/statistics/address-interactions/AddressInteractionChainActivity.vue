<script setup lang="ts">
import type { ChainActivity, SharedDeposit } from './address-interaction-graph';
import { startPromise } from '@shared/utils';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useScramble } from '@/modules/settings/use-scramble';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { historyEventsRoute, useChainLocation, usePagedList } from './address-interaction-panel';

/** The transactions one pair shares on one chain, revealed a page at a time. `color` matches the chain's slice of the split bar above. */
const { activity, color } = defineProps<{ activity: ChainActivity; color: string }>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const { getChainName } = useSupportedChains();
const { scrambleAddress } = useScramble();
const chainLocation = useChainLocation();

const { nextCount, showMore, shown } = usePagedList(() => activity.txHashes);
const bridgeTxHashes = computed<Set<string>>(() => new Set(activity.bridgeTxHashes));
const deposits = computed<Map<string, SharedDeposit>>(() => new Map(activity.sharedDeposits.map(deposit => [deposit.txHash, deposit])));

interface SharedDepositRow {
  exchange?: string;
  /** Names the deposit address the pair shares in the transaction. */
  title: string;
}

interface TransactionRow {
  hash: string;
  isBridge: boolean;
  sharedDeposit?: SharedDepositRow;
}

const rows = computed<TransactionRow[]>(() => get(shown).map((hash) => {
  const deposit = get(deposits).get(hash);
  return {
    hash,
    isBridge: get(bridgeTxHashes).has(hash),
    sharedDeposit: deposit && {
      exchange: deposit.depositExchange,
      title: t('address_interactions.shared_deposit_address', { address: scrambleAddress(deposit.depositAddress) }),
    },
  };
}));

function openInHistory(txHashes: readonly string[]): void {
  startPromise(router.push(historyEventsRoute(chainLocation(activity.chain), txHashes)));
}
</script>

<template>
  <section
    class="flex min-w-0 flex-col gap-2"
    :data-chain="activity.chain"
    data-testid="interaction-chain-activity"
  >
    <div class="flex items-center gap-2">
      <span
        class="size-2.5 shrink-0 rounded-full"
        :style="{ backgroundColor: color }"
        aria-hidden="true"
      />
      <LocationIcon
        :item="activity.chain"
        icon
        size="16px"
      />
      <h4 class="min-w-0 flex-1 truncate text-sm font-medium">
        {{ getChainName(activity.chain) }}
      </h4>
      <RuiChip
        size="sm"
        color="grey"
        class="shrink-0"
      >
        {{ t('address_interactions.tx_count', { count: activity.txHashes.length }, activity.txHashes.length) }}
      </RuiChip>
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="-mr-2 shrink-0"
        :aria-label="t('address_interactions.view_in_history')"
        :title="t('address_interactions.view_in_history')"
        data-testid="interaction-history-link"
        @click="openInHistory(activity.txHashes)"
      >
        <RuiIcon
          name="lu-arrow-up-right"
          size="16"
        />
      </RuiButton>
    </div>
    <ul class="flex min-w-0 flex-col pl-0 divide-y divide-rui-grey-200 rounded-md border border-default dark:divide-rui-grey-800">
      <li
        v-for="row in rows"
        :key="row.hash"
        class="group/row flex min-w-0 flex-col py-1 pl-3 pr-1"
      >
        <div class="flex min-w-0 items-center justify-between gap-2">
          <HashLink
            :text="row.hash"
            :location="activity.chain"
            :truncate-length="8"
            :size="14"
            type="transaction"
            reveal-actions
          />
          <RuiChip
            v-if="row.isBridge"
            size="sm"
            color="primary"
            class="ml-auto shrink-0"
            data-testid="interaction-tx-bridge"
          >
            {{ t('address_interactions.bridge') }}
          </RuiChip>
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="shrink-0"
            :aria-label="t('address_interactions.open_tx_in_history')"
            :title="t('address_interactions.open_tx_in_history')"
            data-testid="interaction-tx-history"
            @click="openInHistory([row.hash])"
          >
            <RuiIcon
              name="lu-arrow-up-right"
              size="16"
            />
          </RuiButton>
        </div>
        <div
          v-if="row.sharedDeposit"
          class="flex min-w-0 items-center gap-2 pb-1 text-caption text-rui-warning"
          :title="row.sharedDeposit.title"
          data-testid="interaction-tx-shared-deposit"
        >
          <LocationIcon
            v-if="row.sharedDeposit.exchange"
            :item="row.sharedDeposit.exchange"
            horizontal
            size="24px"
            data-testid="interaction-deposit-exchange"
          />
          <span class="truncate">{{ t('address_interactions.shared_deposit') }}</span>
        </div>
      </li>
    </ul>
    <RuiButton
      v-if="nextCount > 0"
      variant="text"
      color="primary"
      size="sm"
      data-testid="interaction-tx-show-more"
      @click="showMore()"
    >
      {{ t('address_interactions.show_more', { count: nextCount }) }}
    </RuiButton>
  </section>
</template>
