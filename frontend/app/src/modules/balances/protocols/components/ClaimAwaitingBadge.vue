<script setup lang="ts">
import { type ProtocolBalance, toSentenceCase } from '@rotki/common';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { claimPageUrl } from '@/modules/balances/protocols/claim-pages';
import ClaimRequestRow from '@/modules/balances/protocols/components/ClaimRequestRow.vue';
import { useClaimAwaiting } from '@/modules/balances/protocols/use-claim-awaiting';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { protocolBalance, asset, compact = false } = defineProps<{
  protocolBalance: ProtocolBalance;
  asset?: string;
  /** Show only the icon, for rows that are already crowded. */
  compact?: boolean;
}>();

const open = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

const { accounts, claims, hasReady, isReady } = useClaimAwaiting(() => protocolBalance);

const claimPage = computed<string | undefined>(() => claimPageUrl(protocolBalance.protocol));
const protocolName = computed<string>(() => toSentenceCase(protocolBalance.protocol));
</script>

<template>
  <span
    class="inline-flex"
    @click.stop
  >
    <RuiMenu
      v-model="open"
      lazy
      :options="{ placement: 'bottom-start' }"
    >
      <template #activator="{ attrs }">
        <button
          type="button"
          class="flex items-center gap-1 h-6 px-1.5 rounded-full text-xs font-medium transition-colors"
          :class="hasReady
            ? 'text-rui-success bg-rui-success/10 hover:bg-rui-success/20'
            : 'text-rui-warning bg-rui-warning/10 hover:bg-rui-warning/20'"
          data-testid="claim-awaiting-badge"
          :aria-label="hasReady ? t('common.ready_to_claim') : t('common.awaiting_claim')"
          v-bind="attrs"
        >
          <RuiIcon
            :name="hasReady ? 'lu-circle-check' : 'lu-clock'"
            size="14"
          />
          <span v-if="!compact">{{ hasReady ? t('common.ready_to_claim') : t('common.awaiting_claim') }}</span>
        </button>
      </template>

      <div class="flex flex-col gap-3 p-3 min-w-72 max-w-96">
        <div class="font-medium text-sm">
          {{ t('common.claim_requests', { count: claims.length, protocol: protocolName }, claims.length) }}
        </div>

        <div
          v-if="claims.length > 0"
          class="flex flex-col gap-1"
          data-testid="claim-awaiting-requests"
        >
          <ClaimRequestRow
            v-for="(claim, index) in claims"
            :key="`${claim.account?.address}-${claim.id ?? index}`"
            :claim="claim"
            :asset="asset"
            :ready="isReady(claim)"
          />
        </div>

        <div
          v-else-if="protocolBalance.awaitingClaim"
          class="flex items-center justify-between gap-4 text-sm"
        >
          <span class="text-rui-text-secondary">{{ t('common.awaiting_claim') }}</span>
          <AssetAmountDisplay
            v-if="asset"
            class="font-medium"
            :asset="asset"
            :amount="protocolBalance.awaitingClaim"
          />
          <ValueDisplay
            v-else
            class="font-medium"
            :value="protocolBalance.awaitingClaim"
          />
        </div>

        <div
          v-if="accounts.length > 0"
          class="flex flex-col gap-1"
          data-testid="claim-awaiting-accounts"
        >
          <span class="text-xs text-rui-text-secondary">{{ t('common.claim_with') }}</span>
          <div class="flex flex-col gap-1 max-h-40 overflow-y-auto">
            <HashLink
              v-for="account in accounts"
              :key="`${account.chain}-${account.address}`"
              :text="account.address"
              :location="account.chain"
            />
          </div>
        </div>

        <ExternalLink
          v-if="claimPage"
          :url="claimPage"
          class="text-xs"
          data-testid="claim-awaiting-link"
        >
          {{ t('common.claim_page') }}
        </ExternalLink>
      </div>
    </RuiMenu>
  </span>
</template>
