<script setup lang="ts">
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import PrioritizedList from '@/components/helper/PrioritizedList.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import EnableEnsNamesSetting from '@/components/settings/frontend/EnableEnsNamesSetting.vue';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { PrioritizedListData, type PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import {
  BLOCKCHAIN_ACCOUNT_PRIO_LIST_ITEM,
  ENS_NAMES_PRIO_LIST_ITEM,
  ETHEREUM_TOKENS_PRIO_LIST_ITEM,
  GLOBAL_ADDRESSBOOK_PRIO_LIST_ITEM,
  HARDCODED_MAPPINGS_PRIO_LIST_ITEM,
  type PrioritizedListId,
  PRIVATE_ADDRESSBOOK_PRIO_LIST_ITEM,
} from '@/modules/settings/types/prioritized-list-id';
import { useGeneralSettingsStore } from '@/store/settings/general';

const currentAddressNamePriorities = ref<PrioritizedListId[]>([]);
const { addressNamePriority } = storeToRefs(useGeneralSettingsStore());
const { resetAddressesNames } = useAddressNameResolution();

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
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="addressNamePriority"
    @finished="finishEditing()"
  >
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
        :model-value="currentAddressNamePriorities"
        :all-items="availableCurrentAddressNamePriorities()"
        :disable-add="true"
        :disable-delete="true"
        @update:model-value="updateImmediate($event)"
      />
    </RuiCard>

    <ActionStatusIndicator
      class="mx-[1px] mt-4"
      :status="{ error, success }"
    />
  </SettingsOption>
</template>
