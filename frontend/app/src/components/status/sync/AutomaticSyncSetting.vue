<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { usePremiumStore } from '@/store/session/premium';

defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    disabled?: boolean;
    dense?: boolean;
  }>(),
  {
    dense: false,
    disabled: false,
  },
);

const sync = ref(false);
const { premiumSync } = storeToRefs(usePremiumStore());

watchImmediate(premiumSync, (premiumSync) => {
  set(sync, premiumSync);
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="premiumShouldSync"
  >
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
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
