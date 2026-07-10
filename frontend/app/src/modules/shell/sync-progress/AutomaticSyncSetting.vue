<script setup lang="ts">
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

defineOptions({
  inheritAttrs: false,
});

const { disabled = false, dense = false } = defineProps<{
  disabled?: boolean;
  dense?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

// `premiumShouldSync` is an unregistered backend flag (returned in the `other` bucket and mirrored to
// the premium store), so it is written through the general settings update rather than the registry
// writer; `update()` refreshes the premium store's sync state from the response.
const sync = ref<boolean>(false);
const { premiumSync } = storeToRefs(usePremiumStore());
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();
const { update } = useSettingsOperations();

watchImmediate(premiumSync, (value) => {
  set(sync, value);
});

async function updateSync(value: boolean): Promise<void> {
  clearAll();
  const result = await update({ premiumShouldSync: value });
  if (result.success)
    setSuccess('', true);
  else
    setError(result.message ?? '', true);
}
</script>

<template>
  <RuiSwitch
    v-bind="$attrs"
    v-model="sync"
    data-cy="premium-should-sync"
    :label="t('premium_settings.actions.sync')"
    :hint="t('premium_settings.actions.sync_hint')"
    :success-messages="success"
    :error-messages="error"
    :disabled="disabled"
    :size="dense ? 'sm' : undefined"
    :class="{
      '[&_span]:text-sm [&_span]:mt-0.5': dense,
    }"
    color="primary"
    @update:model-value="updateSync($event)"
  />
</template>
