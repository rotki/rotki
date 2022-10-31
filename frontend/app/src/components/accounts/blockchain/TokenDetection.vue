<template>
  <div class="d-flex align-center justify-end">
    <div class="mr-2">
      {{ detectedTokens.total }}
    </div>
    <div>
      <v-tooltip top>
        <template #activator="{ on }">
          <v-btn
            text
            icon
            :disabled="detectingTokens || loading"
            v-on="on"
            @click="detectTokensAndQueryBalances()"
          >
            <v-progress-circular
              v-if="detectingTokens"
              indeterminate
              color="primary"
              width="2"
              size="20"
            />
            <v-icon v-else small>mdi-refresh</v-icon>
          </v-btn>
        </template>
        <div class="text-center">
          <div>
            {{ tc('account_balances.detect_tokens.tooltip.redetect') }}
          </div>
          <div v-if="detectedTokens.timestamp">
            <i18n path="account_balances.detect_tokens.tooltip.last_detected">
              <template #time>
                <date-display :timestamp="detectedTokens.timestamp" />
              </template>
            </i18n>
          </div>
        </div>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useTokenDetection } from '@/composables/balances/token-detection';

const props = defineProps({
  address: {
    required: true,
    type: String
  },
  loading: {
    required: true,
    type: Boolean
  }
});

const { address } = toRefs(props);

const { detectingTokens, detectedTokens, detectTokensAndQueryBalances } =
  useTokenDetection(address);
const { tc } = useI18n();
</script>
