<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { Defaults } from '@/data/defaults';
import { useGeneralSettingsStore } from '@/store/settings/general';

const DEFAULT = Defaults.BTC_DERIVATION_GAP_LIMIT;

const btcDerivationGapLimit = ref<string>(DEFAULT.toString());
const { btcDerivationGapLimit: limit } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n({ useScope: 'global' });

function successMessage(limit: string) {
  return t('general_settings.validation.btc_derivation_gap.success', {
    limit,
  });
}

function reset(update: (value: number) => void) {
  update(DEFAULT);
  set(btcDerivationGapLimit, DEFAULT.toString());
}

onMounted(() => {
  set(btcDerivationGapLimit, get(limit).toString());
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('general_settings.labels.btc_derivation_gap') }}
    </template>
    <SettingsOption
      #default="{ error, success, update, updateImmediate }"
      setting="btcDerivationGapLimit"
      :error-message="t('general_settings.validation.btc_derivation_gap.error')"
      :success-message="successMessage"
    >
      <div class="flex items-start w-full">
        <RuiTextField
          v-model.number="btcDerivationGapLimit"
          variant="outlined"
          color="primary"
          class="w-full"
          :label="t('general_settings.labels.btc_derivation_gap')"
          type="number"
          :success-messages="success"
          :error-messages="error"
          @update:model-value="update($event ? parseInt($event) : $event)"
        />
        <RuiButton
          class="mt-1 ml-2"
          variant="text"
          icon
          @click="reset(updateImmediate)"
        >
          <RuiIcon name="lu-history" />
        </RuiButton>
      </div>
    </SettingsOption>
  </SettingsItem>
</template>
