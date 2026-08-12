<script setup lang="ts">
import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { boundary } = defineProps<{
  boundary: DivergenceBoundaryEvent;
  asset?: string;
  location?: string;
}>();

const emit = defineEmits<{
  view: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const isMatching = computed<boolean>(() => boundary.color === 'success');

const label = computed<string>(() => isMatching.value
  ? t('balance_divergence.last_matching')
  : t('balance_divergence.first_diverged'));
</script>

<template>
  <div
    class="flex flex-col gap-3 rounded border border-default border-l-[3px] p-4 text-sm"
    :class="isMatching ? 'border-l-rui-success' : 'border-l-rui-warning'"
    data-testid="divergence-boundary"
    :data-key="boundary.key"
  >
    <div class="flex items-center justify-between gap-3">
      <span
        class="inline-flex items-center gap-2 font-medium"
        :class="isMatching ? 'text-rui-success' : 'text-rui-warning'"
      >
        <RuiIcon
          :name="isMatching ? 'lu-check' : 'lu-triangle-alert'"
          size="16"
        />
        {{ label }}
      </span>
      <RuiButton
        variant="outlined"
        color="primary"
        size="sm"
        :disabled="!boundary.event.groupIdentifier"
        data-testid="view-divergence"
        :data-key="boundary.key"
        @click="emit('view')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-arrow-right"
            size="14"
          />
        </template>
        {{ t('balance_divergence.view_event') }}
      </RuiButton>
    </div>

    <div class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-2 text-rui-text-secondary">
      <span>{{ t('balance_divergence.event') }}</span>
      <HashLink
        v-if="boundary.event.groupIdentifier"
        class="justify-self-end"
        :text="boundary.event.groupIdentifier"
        type="transaction"
        :location="location"
        :truncate-length="8"
      />
      <span
        v-else
        class="justify-self-end text-rui-text"
      >
        {{ t('balance_divergence.missing_group') }}
      </span>

      <span>{{ t('balance_divergence.block') }}</span>
      <span class="justify-self-end text-rui-text">{{ boundary.event.blockNumber }}</span>

      <span>{{ t('balance_divergence.tracked') }}</span>
      <AssetAmountDisplay
        class="justify-self-end text-rui-text"
        :amount="boundary.event.trackedBalance"
        :asset="asset"
        no-collection-parent
      />

      <span>{{ t('balance_divergence.onchain') }}</span>
      <AssetAmountDisplay
        class="justify-self-end text-rui-text"
        :amount="boundary.event.onchainBalance"
        :asset="asset"
        no-collection-parent
      />

      <span>{{ t('balance_divergence.difference') }}</span>
      <AssetAmountDisplay
        class="justify-self-end text-rui-text"
        :amount="boundary.event.difference"
        :asset="asset"
        no-collection-parent
      />
    </div>
  </div>
</template>
