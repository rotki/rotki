<template>
  <div>
    <div
      class="text-subtitle-1"
      v-text="t('eth_address_book.hint.priority.title')"
    />
    <v-sheet outlined rounded class="mt-4">
      <settings-option
        #default="{ error, success, update }"
        setting="addressNamePriority"
        @finished="resetCurrentAddressNamePriorities"
      >
        <address-name-priority-selection
          :value="currentAddressNamePriorities"
          :status="{ error, success }"
          @input="update"
        />
      </settings-option>
    </v-sheet>
  </div>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import AddressNamePrioritySelection from '@/components/settings/frontend/AddressNamePrioritySelection.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const currentAddressNamePriorities = ref<string[]>([]);

const { addressNamePriority } = storeToRefs(useGeneralSettingsStore());

const resetCurrentAddressNamePriorities = () => {
  set(currentAddressNamePriorities, get(addressNamePriority));
};

onMounted(() => {
  resetCurrentAddressNamePriorities();
});
const { t } = useI18n();
</script>
