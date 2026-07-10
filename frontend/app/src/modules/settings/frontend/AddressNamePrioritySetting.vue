<script setup lang="ts">
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
import ActionStatusIndicator from '@/modules/shell/components/error/ActionStatusIndicator.vue';
import PrioritizedList from '@/modules/shell/components/PrioritizedList.vue';

const { resetAddressesNames } = useAddressNameResolution();
const { error: writeError, model, success: writeSuccess } = useSettingModel('addressNamePriority', { debounce: 0 });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

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
    setSuccess('', true);
    resetAddressesNames();
  }
});

watch(writeError, (message) => {
  if (message)
    setError(message, true);
});
</script>

<template>
  <RuiCard
    rounded="md"
    no-padding
    class="overflow-hidden h-auto"
  >
    <div class="pl-8 pt-2 border-b border-default">
      <EnableEnsNamesSetting />
    </div>
    <PrioritizedList
      variant="flat"
      :model-value="model"
      :all-items="availableCurrentAddressNamePriorities()"
      :disable-add="true"
      :disable-delete="true"
      @update:model-value="updatePriorities($event)"
    />
  </RuiCard>

  <ActionStatusIndicator
    class="mx-[1px] mt-4"
    :status="{ error, success }"
  />
</template>
