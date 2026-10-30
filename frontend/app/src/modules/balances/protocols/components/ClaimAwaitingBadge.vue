<script setup lang="ts">
import { type ProtocolBalance, toSentenceCase } from '@rotki/common';
import { claimPageUrl } from '@/modules/balances/protocols/claim-pages';
import ClaimAmount from '@/modules/balances/protocols/components/ClaimAmount.vue';
import ClaimRequestRow from '@/modules/balances/protocols/components/ClaimRequestRow.vue';
import ClaimStatusLabel from '@/modules/balances/protocols/components/ClaimStatusLabel.vue';
import { useClaimAwaiting } from '@/modules/balances/protocols/use-claim-awaiting';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { protocolBalance, asset, compact = false } = defineProps<{
  protocolBalance: ProtocolBalance;
  asset?: string;
  /** Show only the icon, with the status in a tooltip, for rows that are already crowded. */
  compact?: boolean;
}>();

const open = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

const { accounts, claims, isReady, status, statusAmount } = useClaimAwaiting(() => protocolBalance);
const { protocolData } = useProtocolData(() => protocolBalance.protocol);

const claimPage = computed<string | undefined>(() => claimPageUrl(protocolBalance.protocol));
const protocolName = computed<string>(() => get(protocolData)?.name ?? toSentenceCase(protocolBalance.protocol));
const ready = computed<boolean>(() => get(status).kind === 'ready');
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
        <RuiTooltip
          :disabled="!compact || open"
          :open-delay="200"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <button
              type="button"
              class="flex items-center gap-1 h-6 px-1.5 rounded-full text-xs font-medium transition-colors"
              :class="ready
                ? 'text-rui-success bg-rui-success/10 hover:bg-rui-success/20'
                : 'text-rui-text-secondary bg-rui-grey-200 hover:bg-rui-grey-300 dark:bg-rui-grey-800 dark:hover:bg-rui-grey-700'"
              data-testid="claim-awaiting-badge"
              :aria-label="ready ? t('claims.status.ready') : t('claims.status.pending')"
              v-bind="attrs"
            >
              <RuiIcon
                :name="ready ? 'lu-circle-check' : 'lu-clock'"
                size="14"
              />
              <ClaimStatusLabel
                v-if="!compact"
                :status="status"
              />
            </button>
          </template>
          <i18n-t
            v-if="ready"
            keypath="claims.tooltip.ready"
            scope="global"
            tag="span"
            class="flex items-center gap-1"
            data-testid="claim-awaiting-tooltip"
          >
            <template #amount>
              <ClaimAmount
                :asset="asset"
                :amount="statusAmount"
              />
            </template>
            <template #protocol>
              {{ protocolName }}
            </template>
          </i18n-t>
          <i18n-t
            v-else
            keypath="claims.tooltip.pending"
            scope="global"
            tag="span"
            class="flex items-center gap-1"
            data-testid="claim-awaiting-tooltip"
          >
            <template #amount>
              <ClaimAmount
                :asset="asset"
                :amount="statusAmount"
              />
            </template>
            <template #protocol>
              {{ protocolName }}
            </template>
          </i18n-t>
        </RuiTooltip>
      </template>

      <div class="flex flex-col gap-3 p-3 min-w-72 max-w-96">
        <div
          class="font-medium text-sm"
          data-testid="claim-awaiting-heading"
        >
          {{ t('claims.requests', { count: claims.length, protocol: protocolName }, claims.length) }}
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
          <span class="text-rui-text-secondary">{{ t('claims.status.pending') }}</span>
          <ClaimAmount
            class="font-medium"
            :asset="asset"
            :amount="protocolBalance.awaitingClaim"
          />
        </div>

        <div
          v-if="accounts.length > 0"
          class="flex flex-col gap-1"
          data-testid="claim-awaiting-accounts"
        >
          <span class="text-xs text-rui-text-secondary">{{ t('claims.claim_with') }}</span>
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
          custom
          class="block"
          data-testid="claim-awaiting-link"
        >
          <RuiButton
            color="primary"
            variant="outlined"
            size="sm"
            class="w-full"
          >
            {{ t('claims.open_page') }}
            <template #append>
              <RuiIcon
                name="lu-external-link"
                size="14"
              />
            </template>
          </RuiButton>
        </ExternalLink>
      </div>
    </RuiMenu>
  </span>
</template>
