<script setup lang="ts">
import { useLocationStore } from '@/modules/core/common/use-location-store';
import {
  historyLimitMessage,
  showsKeyWaitingTimeWarning,
} from '@/modules/settings/api-keys/exchange/exchange-keys-form';

/**
 * What the form has to say about the chosen exchange before its keys are saved. All three notices
 * are decided by the exchange alone, so they need nothing from the form itself.
 */
const { location } = defineProps<{
  location: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useIsExperimentalExchange } = useLocationStore();
const experimental = useIsExperimentalExchange(() => location);

const showsWaitingTime = computed<boolean>(() => showsKeyWaitingTimeWarning(location));

const limitMessage = computed<string>(() => {
  const key = historyLimitMessage(location);
  return key ? t(key) : '';
});
</script>

<template>
  <RuiAlert
    v-if="showsWaitingTime"
    class="mt-4"
    type="info"
  >
    {{ t('exchange_keys_form.waiting_time_warning') }}
  </RuiAlert>

  <RuiAlert
    v-if="limitMessage"
    class="mt-4"
    type="warning"
  >
    {{ limitMessage }}
  </RuiAlert>

  <RuiAlert
    v-if="experimental"
    type="info"
    class="mt-4"
  >
    {{ t('exchange_settings.inputs.experimental') }}
  </RuiAlert>
</template>
