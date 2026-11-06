<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';

interface Props {
  hasBalance: boolean;
  includedValue: BigNumber | undefined;
  loading: boolean;
  pending: boolean;
  value: BigNumber;
}

defineProps<Props>();

const { t } = useI18n({ useScope: 'global' });

const pendingValue = '\u{2014}';
</script>

<template>
  <div class="flex flex-col items-end justify-end">
    <div
      v-if="includedValue && !loading && (!pending || hasBalance)"
      class="text-xs"
    >
      <FiatDisplay
        v-if="includedValue"
        :value="includedValue"
      />
      /
    </div>
    <span
      v-if="pending && !loading && !hasBalance"
      data-testid="account-balance-pending"
    >
      {{ pendingValue }}
    </span>
    <div
      v-else
      class="flex items-center gap-1"
    >
      <RuiTooltip v-if="pending && !loading">
        <template #activator>
          <RuiIcon
            name="lu-info"
            size="14"
            data-testid="account-balance-partial"
          />
        </template>
        {{ t('account_balances.pending_value') }}
      </RuiTooltip>
      <FiatDisplay
        :value="value"
        :loading="loading"
        data-testid="usd-value"
        class="font-medium"
      />
    </div>
  </div>
</template>
