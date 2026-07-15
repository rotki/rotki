<script setup lang="ts">
import { toCapitalCase } from '@rotki/common';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import SettingMultiSelect from '@/modules/settings/controls/SettingMultiSelect.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { SUPPRESSIBLE_SERVICES, SuppressibleMissingKeyService } from '@/modules/settings/types/user-settings';
import AppImage from '@/modules/shell/components/AppImage.vue';

const { t } = useI18n({ useScope: 'global' });

const SERVICE_ICONS: Record<SuppressibleMissingKeyService, string> = {
  [SuppressibleMissingKeyService.BEACONCHAIN]: getPublicServiceImagePath('beaconchain.svg'),
  [SuppressibleMissingKeyService.BLOCKSCOUT]: getPublicServiceImagePath('blockscout.svg'),
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

  <SettingsItem
    setting-key="suppressMissingKeyMsgServices"
    data-testid="suppress-missing-key-services-setting"
  >
    <template #subtitle>
      {{ t('general_settings.external_service_setting.suppress_missing_key.subtitle') }}
    </template>
    <SettingMultiSelect
      setting="suppressMissingKeyMsgServices"
      :options="serviceOptions"
      key-attr="id"
      text-attr="name"
      :bulk-actions="{
        clearLabel: t('general_settings.external_service_setting.suppress_missing_key.clear_all'),
        selectLabel: t('general_settings.external_service_setting.suppress_missing_key.suppress_all'),
      }"
      :label="t('general_settings.external_service_setting.suppress_missing_key.label')"
      data-testid="suppress-missing-key-services"
      :item-height="48"
      :success-message="t('general_settings.external_service_setting.suppress_missing_key.success')"
      :error-message="t('general_settings.external_service_setting.suppress_missing_key.error')"
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
    </SettingMultiSelect>
  </SettingsItem>
</template>
