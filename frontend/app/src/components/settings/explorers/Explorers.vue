<template>
  <div class="explorers mt-8">
    <div class="text-h6">
      {{ t('explorers.title') }}
    </div>
    <div class="text-subtitle-1">
      {{ t('explorers.subtitle') }}
    </div>

    <v-select
      v-model="selection"
      class="mt-4"
      outlined
      :items="supportedExplorers"
      :label="t('explorers.chain_selector')"
      @change="onChange"
    >
      <template #item="{ item }">
        <asset-details :asset="item" />
      </template>
      <template #selection="{ item }">
        <asset-details :asset="item" />
      </template>
    </v-select>

    <v-text-field
      v-model="address"
      outlined
      clearable
      :label="t('explorers.address')"
      :hint="t('explorers.address_url', { addressUrl })"
      :placeholder="addressUrl"
      persistent-hint
      @click:clear="saveAddress()"
    >
      <template #append-outer>
        <v-btn
          icon
          :disabled="!isValid(address)"
          class="mt-n2"
          @click="saveAddress(address)"
        >
          <v-icon>mdi-content-save</v-icon>
        </v-btn>
      </template>
    </v-text-field>
    <v-text-field
      v-model="tx"
      outlined
      clearable
      :label="t('explorers.tx')"
      :hint="t('explorers.tx_url', { txUrl })"
      :placeholder="txUrl"
      persistent-hint
      @click:clear="saveTransaction()"
    >
      <template #append-outer>
        <v-btn
          icon
          :disabled="!isValid(tx)"
          class="mt-n2"
          @click="saveTransaction(tx)"
        >
          <v-icon>mdi-content-save</v-icon>
        </v-btn>
      </template>
    </v-text-field>
  </div>
</template>

<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { explorerUrls } from '@/types/asset-urls';

const ETC = 'ETC' as const;

const supportedExplorers = [...Object.values(Blockchain), ETC];

const selection = ref<Blockchain | typeof ETC>(Blockchain.ETH);
const store = useFrontendSettingsStore();
const { explorers } = storeToRefs(store);

const address = ref<string>('');
const tx = ref<string>('');

const txUrl = computed<string>(() => {
  const setting = get(explorers)[get(selection)];
  return setting?.transaction ?? explorerUrls[get(selection)].transaction;
});

const addressUrl = computed<string>(() => {
  const setting = get(explorers)[get(selection)];
  return setting?.address ?? explorerUrls[get(selection)].address;
});

const onChange = () => {
  const setting = get(explorers)[get(selection)];
  set(address, setting?.address ?? '');
  set(tx, setting?.transaction ?? '');
};

onMounted(() => {
  onChange();
});

const isValid = (entry: string | null): boolean => {
  return !entry ? false : entry.length > 0;
};

const saveAddress = async (newAddress?: string) => {
  set(address, newAddress ?? '');
  const setting = get(explorers)[get(selection)];

  const updated = {
    ...setting,
    address: newAddress
  };

  if (!newAddress) {
    delete updated.address;
  }

  await store.updateSetting({
    explorers: {
      ...get(explorers),
      [get(selection)]: updated
    }
  });
};

const saveTransaction = async (newTransaction?: string) => {
  const setting = get(explorers)[get(selection)];

  const updated = {
    ...setting,
    transaction: newTransaction
  };

  if (!newTransaction) {
    delete updated.transaction;
  }

  await store.updateSetting({
    explorers: {
      ...get(explorers),
      [get(selection)]: updated
    }
  });
};

const { t } = useI18n();
</script>

<style scoped lang="scss">
.explorers {
  :deep() {
    .v-select {
      &__slot {
        height: 76px;

        /* stylelint-disable */
        .v-label:not(.v-label--active) {
          /* stylelint-enable */
          top: 26px;
        }
      }
    }

    .v-input {
      &__icon {
        &--append {
          padding-top: 16px;
        }
      }
    }
  }
}
</style>
