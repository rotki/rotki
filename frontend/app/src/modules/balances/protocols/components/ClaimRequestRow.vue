<script setup lang="ts">
import type { ClaimRequest } from '@rotki/common';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { useScramble } from '@/modules/settings/use-scramble';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { claim, asset, ready } = defineProps<{
  claim: ClaimRequest;
  asset?: string;
  /** The request can be claimed right now. */
  ready: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { scrambleIdentifier } = useScramble();
</script>

<template>
  <div
    class="flex items-center justify-between gap-4 rounded bg-rui-grey-100 dark:bg-rui-grey-800 px-2 py-1.5 text-sm"
    data-testid="claim-awaiting-request"
  >
    <div class="flex flex-wrap items-center gap-x-1">
      <span v-if="claim.id">#{{ scrambleIdentifier(claim.id) }}</span>
      <span
        v-if="ready"
        class="text-rui-success"
      >
        {{ t('claims.request.ready') }}
      </span>
      <i18n-t
        v-else-if="claim.availableAt"
        keypath="claims.request.ready_on"
        scope="global"
        tag="span"
        class="text-rui-text-secondary"
      >
        <template #date>
          <DateDisplay
            :timestamp="claim.availableAt"
            no-time
          />
        </template>
      </i18n-t>
      <i18n-t
        v-else-if="claim.requestedAt"
        keypath="claims.request.requested"
        scope="global"
        tag="span"
        class="text-rui-text-secondary"
      >
        <template #date>
          <DateDisplay
            :timestamp="claim.requestedAt"
            no-time
          />
        </template>
      </i18n-t>
      <span
        v-else
        class="text-rui-text-secondary"
      >
        {{ t('claims.status.pending') }}
      </span>
    </div>
    <AssetAmountDisplay
      v-if="asset"
      :asset="asset"
      :amount="claim.amount"
    />
    <ValueDisplay
      v-else
      :value="claim.amount"
    />
  </div>
</template>
