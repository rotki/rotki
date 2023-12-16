<script setup lang="ts">
const props = defineProps<{
  address: string;
  loading: boolean;
  chain: string;
}>();

const { address, chain } = toRefs(props);

const { detectingTokens, detectedTokens, detectTokens } = useTokenDetection(chain, address);

const { t } = useI18n();
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
            name="restart-line"
          />
        </RuiButton>
      </template>
      <div class="text-center">
        <div>
          {{ t('account_balances.detect_tokens.tooltip.redetect') }}
        </div>
        <div v-if="detectedTokens.timestamp">
          <i18n-t
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
