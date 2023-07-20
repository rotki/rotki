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
  <div class="d-flex align-center justify-end">
    <div class="mr-2">
      {{ detectedTokens.total }}
    </div>
    <div>
      <VTooltip top>
        <template #activator="{ on }">
          <VBtn
            text
            icon
            :disabled="detectingTokens || loading"
            v-on="on"
            @click="detectTokens()"
          >
            <VProgressCircular
              v-if="detectingTokens"
              indeterminate
              color="primary"
              width="2"
              size="20"
            />
            <VIcon v-else small>mdi-refresh</VIcon>
          </VBtn>
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
      </VTooltip>
    </div>
  </div>
</template>
