<script setup lang="ts">
import { useTokenDetectionUi } from '@/modules/balances/blockchain/use-token-detection-ui';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { address, loading, chains } = defineProps<{
  address: string;
  loading: boolean;
  chains: string[];
}>();

const { detectedTokens, detectingTokens, detectionDisabled, detectTokens } = useTokenDetectionUi(() => chains, () => address);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <!-- an entry of the row's actions menu: the line under the title says what the last run found -->
  <RuiButton
    variant="list"
    :disabled="detectingTokens || loading || detectionDisabled"
    data-testid="token-detection"
    @click="detectTokens()"
  >
    <template #prepend>
      <RuiProgress
        v-if="detectingTokens"
        variant="indeterminate"
        circular
        size="18"
        thickness="2"
      />
      <RuiIcon
        v-else
        size="18"
        name="lu-rotate-ccw"
      />
    </template>
    <span class="flex flex-col items-start text-left">
      <span>{{ t('account_balances.detect_tokens.tooltip.redetect') }}</span>
      <span
        class="text-caption font-normal text-rui-text-secondary whitespace-normal"
        data-testid="token-detection-count"
      >
        <template v-if="detectionDisabled">
          {{ t('account_balances.detect_tokens.tooltip.disabled') }}
        </template>
        <template v-else>
          {{ t('account_balances.detect_tokens.tooltip.detected', { count: detectedTokens.total }) }}
          <i18n-t
            v-if="detectedTokens.timestamp"
            scope="global"
            keypath="account_balances.detect_tokens.tooltip.last_detected"
            tag="span"
            class="before:content-['·'] before:mx-1"
          >
            <template #time>
              <DateDisplay :timestamp="detectedTokens.timestamp" />
            </template>
          </i18n-t>
        </template>
      </span>
    </span>
  </RuiButton>
</template>
