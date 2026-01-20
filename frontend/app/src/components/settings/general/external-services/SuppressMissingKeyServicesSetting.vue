<script setup lang="ts">
import { toCapitalCase } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { SUPPRESSIBLE_SERVICES, SuppressibleMissingKeyService } from '@/types/user';
import { getPublicServiceImagePath } from '@/utils/file';

const { t } = useI18n({ useScope: 'global' });
const { suppressMissingKeyMsgServices } = storeToRefs(useGeneralSettingsStore());

const SERVICE_ICONS: Record<SuppressibleMissingKeyService, string> = {
  [SuppressibleMissingKeyService.BEACONCHAIN]: getPublicServiceImagePath('beaconchain.svg'),
  [SuppressibleMissingKeyService.ETHERSCAN]: getPublicServiceImagePath('etherscan.svg'),
  [SuppressibleMissingKeyService.HELIUS]: getPublicServiceImagePath('helius.svg'),
  [SuppressibleMissingKeyService.THEGRAPH]: getPublicServiceImagePath('thegraph.svg'),
};

interface ServiceOption {
  id: SuppressibleMissingKeyService;
  name: string;
  icon: string;
}

const serviceOptions = computed<ServiceOption[]>(() =>
  SUPPRESSIBLE_SERVICES.map(service => ({
    icon: SERVICE_ICONS[service],
    id: service,
    name: toCapitalCase(service),
  })),
);

const allSelected = computed<boolean>(() => get(suppressMissingKeyMsgServices).length === SUPPRESSIBLE_SERVICES.length);
const noneSelected = computed<boolean>(() => get(suppressMissingKeyMsgServices).length === 0);

function selectAll(updateImmediate: (value: SuppressibleMissingKeyService[]) => void): void {
  updateImmediate([...SUPPRESSIBLE_SERVICES]);
}

function deselectAll(updateImmediate: (value: SuppressibleMissingKeyService[]) => void): void {
  updateImmediate([]);
}

const [DefineServiceItem, ReuseServiceItem] = createReusableTemplate<{ item: ServiceOption; size: string }>();
</script>

<template>
  <DefineServiceItem #default="{ item, size }">
    <div class="flex items-center gap-2">
      <AppImage
        :src="item.icon"
        :size="size"
        class="icon-bg"
        contain
      />
      <span>{{ item.name }}</span>
    </div>
  </DefineServiceItem>

  <SettingsItem data-cy="suppress-missing-key-services-setting">
    <template #title>
      {{ t('general_settings.external_service_setting.suppress_missing_key.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.external_service_setting.suppress_missing_key.subtitle') }}
    </template>
    <SettingsOption
      #default="{ error, success, updateImmediate, loading }"
      setting="suppressMissingKeyMsgServices"
      :error-message="t('general_settings.external_service_setting.suppress_missing_key.error')"
      :success-message="t('general_settings.external_service_setting.suppress_missing_key.success')"
    >
      <div class="flex flex-col gap-2">
        <div class="flex gap-2">
          <RuiButton
            variant="text"
            size="sm"
            color="primary"
            :disabled="loading || allSelected"
            @click="selectAll(updateImmediate)"
          >
            {{ t('general_settings.external_service_setting.suppress_missing_key.suppress_all') }}
          </RuiButton>
          <RuiButton
            variant="text"
            size="sm"
            color="primary"
            :disabled="loading || noneSelected"
            @click="deselectAll(updateImmediate)"
          >
            {{ t('general_settings.external_service_setting.suppress_missing_key.clear_all') }}
          </RuiButton>
        </div>
        <RuiAutoComplete
          :options="serviceOptions"
          :label="t('general_settings.external_service_setting.suppress_missing_key.label')"
          :model-value="suppressMissingKeyMsgServices"
          :success-messages="success"
          :error-messages="error"
          data-cy="suppress-missing-key-services"
          variant="outlined"
          key-attr="id"
          text-attr="name"
          chips
          :item-height="48"
          auto-select-first
          @update:model-value="updateImmediate($event)"
        >
          <template #selection="{ item }">
            <ReuseServiceItem
              :item="item"
              size="1.25rem"
            />
          </template>
          <template #item="{ item }">
            <ReuseServiceItem
              :item="item"
              size="1.5rem"
            />
          </template>
        </RuiAutoComplete>
      </div>
    </SettingsOption>
  </SettingsItem>
</template>
