<script setup lang="ts">
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const { t } = useI18n({ useScope: 'global' });

const { showEvmQueryIndicator } = storeToRefs(useFrontendSettingsStore());
const { updateSetting } = useFrontendSettingsStore();
const { processing } = useHistoryEventsStatus();

function toggleEvmQueryIndicator() {
  updateSetting({ showEvmQueryIndicator: !get(showEvmQueryIndicator) });
}
</script>

<template>
  <RuiTooltip :open-delay="400">
    <template #activator>
      <RuiButton
        variant="text"
        class="!text-rui-text-secondary"
        icon
        @click="toggleEvmQueryIndicator()"
      >
        <RuiBadge
          :model-value="processing"
          color="primary"
          dot
          placement="top"
          offset-y="4"
          size="lg"
          class="flex items-center"
        >
          <RuiIcon name="lu-scroll-text" />
        </RuiBadge>
      </RuiButton>
    </template>
    {{ showEvmQueryIndicator ? t('app_indicators.evm_query_indicator.hide') : t('app_indicators.evm_query_indicator.show') }}
  </RuiTooltip>
</template>
