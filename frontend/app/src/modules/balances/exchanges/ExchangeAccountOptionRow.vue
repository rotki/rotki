<script setup lang="ts">
import type { ExchangeAccountOption } from '@/modules/balances/exchanges/use-exchange-account-selection';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';

const { account, selected } = defineProps<{
  account: ExchangeAccountOption;
  selected: boolean;
}>();

const emit = defineEmits<{
  pick: [identifier: string];
}>();

defineSlots<{
  prepend?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

/** An account holding nothing above the threshold is muted, though still pickable. */
const isEmpty = computed<boolean>(() => account.loaded && account.value.isZero());
</script>

<template>
  <RuiButton
    variant="list"
    class="w-full"
    :class="{ 'bg-rui-primary-subtle': selected, 'opacity-60': isEmpty && !selected }"
    :aria-pressed="selected"
    data-testid="exchange-account-option"
    :data-account="account.identifier"
    :data-empty="isEmpty"
    @click="emit('pick', account.identifier)"
  >
    <span class="flex items-center gap-2 w-full min-w-0">
      <slot name="prepend" />
      <RuiTooltip
        v-if="account.error"
        class="inline-flex shrink-0"
        :options="{ placement: 'left' }"
        :open-delay="200"
      >
        <template #activator>
          <RuiIcon
            name="lu-triangle-alert"
            size="16"
            color="warning"
            data-testid="exchange-account-option-failed"
          />
          <span class="sr-only">{{ t('exchange_balances.accounts.failed') }}</span>
        </template>
        {{ t('exchange_balances.accounts.failed_tooltip', { error: account.error }) }}
      </RuiTooltip>
      <span class="truncate text-left">{{ account.name }}</span>
      <span
        v-if="account.loaded"
        class="ms-auto flex shrink-0 items-baseline gap-2 text-rui-text-secondary"
      >
        <FiatDisplay
          :value="account.value"
          no-tooltip
        />
        <PercentageDisplay
          v-if="account.share"
          class="w-14 text-xs"
          :value="account.share"
        />
        <span
          v-else
          class="w-14"
        />
      </span>
      <span
        v-else
        class="ms-auto shrink-0 text-rui-text-secondary"
        data-testid="exchange-account-option-unknown"
      >
        {{ t('exchange_balances.accounts.unknown') }}
      </span>
    </span>
  </RuiButton>
</template>
