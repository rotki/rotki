<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

const props = defineProps<{
  address: string;
  loading: boolean;
  blockchain: Blockchain;
}>();

const { address, blockchain } = toRefs(props);

const { detectingTokens, detectedTokens, detectTokens } = useTokenDetection(
  blockchain,
  address
);

const { t } = useI18n();
</script>

<template>
  <div class="flex items-center justify-end">
    <div class="mr-2">
      {{ detectedTokens.total }}
    </div>
    <div>
      <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
        <template #activator>
          <RuiButton
            variant="text"
            icon
            :disabled="detectingTokens || loading"
            class="[&_span]:!flex [&_span]:items-center"
            color="primary"
            @click="detectTokens()"
          >
            <RuiProgress
              v-if="detectingTokens"
              variant="indeterminate"
              circular
              size="16"
              thickness="2"
            />

            <RuiIcon v-else size="16" name="restart-line" />
          </RuiButton>
        </template>
        <div class="text-center">
          <div>
            {{ t('account_balances.detect_tokens.tooltip.redetect') }}
          </div>
          <div v-if="detectedTokens.timestamp">
            <i18n path="account_balances.detect_tokens.tooltip.last_detected">
              <template #time>
                <DateDisplay :timestamp="detectedTokens.timestamp" />
              </template>
            </i18n>
          </div>
        </div>
      </RuiTooltip>
    </div>
  </div>
</template>
