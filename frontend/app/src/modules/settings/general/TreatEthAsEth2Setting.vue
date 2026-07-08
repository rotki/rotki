<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useSetting } from '@/modules/settings/use-setting';

const treatEth2asEth = ref<boolean>(false);
const enabled = useSetting('treatEth2AsEth');

onMounted(() => {
  set(treatEth2asEth, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="treatEth2AsEth"
    :error-message="t('general_settings.validation.treat_eth2_as_eth.error')"
  >
    <RuiSwitch
      v-model="treatEth2asEth"
      color="primary"
      :label="t('general_settings.labels.treat_eth2_as_eth')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
