<script setup lang="ts">
import DetectEvmAccounts from '@/components/accounts/balances/DetectEvmAccounts.vue';
import DetectTokenChainsSelection from '@/components/accounts/balances/DetectTokenChainsSelection.vue';

interface Props {
  isEvm: boolean;
  isDetectingTokens: boolean;
  refreshDisabled: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  'redetect:all': [];
}>();

const { t } = useI18n({ useScope: 'global' });

function onRedetectAll(): void {
  emit('redetect:all');
}
</script>

<template>
  <div
    class="flex items-center gap-2 flex-1"
    :class="{ 'hidden lg:block': !isEvm }"
  >
    <template v-if="isEvm">
      <RuiButtonGroup
        variant="outlined"
        color="primary"
      >
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              class="py-2 !outline-0 rounded-none"
              variant="outlined"
              color="primary"
              :loading="isDetectingTokens"
              :disabled="refreshDisabled"
              @click="onRedetectAll()"
            >
              <template #prepend>
                <RuiIcon name="lu-refresh-ccw" />
              </template>

              {{ t('account_balances.detect_tokens.tooltip.redetect') }}
            </RuiButton>
          </template>
          {{ t('account_balances.detect_tokens.tooltip.redetect_all') }}
        </RuiTooltip>

        <DetectTokenChainsSelection @redetect:all="onRedetectAll()" />
      </RuiButtonGroup>

      <DetectEvmAccounts />
    </template>
  </div>
</template>
