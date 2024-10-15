<script setup lang="ts">
import { PrioritizedListData, type PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import {
  BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM,
  ENS_NAMES_PRIO_LIST_ITEM,
  ETHEREUM_TOKENS_PRIO_LIST_ITEM,
  GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM,
  HARDCODED_MAPPINGS_PRIO_LIST_ITEM,
  PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM,
  type PrioritizedListId,
} from '@/types/settings/prioritized-list-id';

const currentAddressNamePriorities = ref<PrioritizedListId[]>([]);
const { addressNamePriority } = storeToRefs(useGeneralSettingsStore());
const { resetAddressesNames } = useAddressesNamesStore();

function finishEditing() {
  resetCurrentAddressNamePriorities();
  resetAddressesNames();
}

function resetCurrentAddressNamePriorities() {
  set(currentAddressNamePriorities, get(addressNamePriority));
}

function availableCurrentAddressNamePriorities(): PrioritizedListData<PrioritizedListId> {
  const itemData: Array<PrioritizedListItemData<PrioritizedListId>> = [
    BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM,
    ENS_NAMES_PRIO_LIST_ITEM,
    ETHEREUM_TOKENS_PRIO_LIST_ITEM,
    GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM,
    HARDCODED_MAPPINGS_PRIO_LIST_ITEM,
    PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM,
  ];
  return new PrioritizedListData(itemData);
}

onMounted(() => {
  resetCurrentAddressNamePriorities();
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="addressNamePriority"
    @finished="finishEditing()"
  >
    <PrioritizedList
      :model-value="currentAddressNamePriorities"
      :all-items="availableCurrentAddressNamePriorities()"
      :item-data-name="t('frontend_settings.alias_names.address_name_priority_setting.data_name')"
      :disable-add="true"
      :disable-delete="true"
      :status="{ error, success }"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
