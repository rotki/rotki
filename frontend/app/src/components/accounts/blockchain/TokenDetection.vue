<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useTokenDetection } from '@/composables/balances/token-detection';

const props = defineProps<{
  address: string;
  loading: boolean;
  chain: string;
}>();

const { address, chain } = toRefs(props);

const { detectedTokens, detectingTokens, detectTokens } = useTokenDetection(chain, address);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center justify-end">
    {{ detectedTokens.total }}
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
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

          <RuiIcon
            v-else
            size="16"
            name="lu-rotate-ccw"
          />
        </RuiButton>
      </template>
      <div class="text-center">
        <div>
          {{ t('account_balances.detect_tokens.tooltip.redetect') }}
        </div>
        <div v-if="detectedTokens.timestamp">
          <i18n-t
            scope="global"
            keypath="account_balances.detect_tokens.tooltip.last_detected"
            tag="span"
          >
            <template #time>
              <DateDisplay :timestamp="detectedTokens.timestamp" />
            </template>
          </i18n-t>
        </div>
      </div>
    </RuiTooltip>
  </div>
</template>
