<script setup lang="ts">
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import EnableEnsNamesSetting from '@/modules/settings/frontend/EnableEnsNamesSetting.vue';
import { PrioritizedListData, type PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import {
  BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM,
  ENS_NAMES_PRIO_LIST_ITEM,
  ETHEREUM_TOKENS_PRIO_LIST_ITEM,
  GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM,
  GNS_NAMES_PRIO_LIST_ITEM,
  HARDCODED_MAPPINGS_PRIO_LIST_ITEM,
  type PrioritizedListId,
  PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM,
} from '@/modules/settings/types/prioritized-list-id';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';

const { t } = useI18n({ useScope: 'global' });

const { resetAddressesNames } = useAddressNameResolution();
const { error: writeError, model, success: writeSuccess } = useSettingModel('addressNamePriority', { debounce: 0 });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

const status = computed<BaseMessage>(() => ({ error: get(error), success: get(success) }));

/**
 * Sources can't be removed, so the add picker only matters for one missing from the saved order,
 * such as a source introduced after the order was saved.
 */
const hasMissingSource = computed<boolean>(() => {
  const current: string[] = get(model);
  return Object.values(AddressNamePriority).some(source => !current.includes(source));
});

const addressNamePriorityValues: string[] = Object.values(AddressNamePriority);

function isAddressNamePriority(value: PrioritizedListId): value is AddressNamePriority {
  return addressNamePriorityValues.includes(value);
}

function availableCurrentAddressNamePriorities(): PrioritizedListData<PrioritizedListId> {
  const itemData: Array<PrioritizedListItemData<PrioritizedListId>> = [
    BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM,
    ENS_NAMES_PRIO_LIST_ITEM,
    ETHEREUM_TOKENS_PRIO_LIST_ITEM,
    GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM,
    GNS_NAMES_PRIO_LIST_ITEM,
    HARDCODED_MAPPINGS_PRIO_LIST_ITEM,
    PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM,
  ];
  return new PrioritizedListData(itemData);
}

function updatePriorities(value: PrioritizedListId[]): void {
  set(model, value.filter(isAddressNamePriority));
}

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved) {
    setSuccess(t('frontend_settings.alias_names.saved'), true);
    resetAddressesNames();
  }
});

watch(writeError, (message) => {
  if (message)
    setError(message, true);
});
</script>

<template>
  <div class="flex flex-col gap-3">
    <EnableEnsNamesSetting />
    <PrioritizedList
      variant="outlined"
      :model-value="model"
      :all-items="availableCurrentAddressNamePriorities()"
      :status="status"
      :item-data-name="t('frontend_settings.alias_names.data_name')"
      :disable-add="!hasMissingSource"
      disable-delete
      @update:model-value="updatePriorities($event)"
    />
  </div>
</template>
