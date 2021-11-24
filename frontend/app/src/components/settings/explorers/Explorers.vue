<template>
  <div class="explorers">
    <div class="text-h6 mt-4">
      {{ $t('explorers.title') }}
    </div>
    <div class="text-subtitle-1">
      {{ $t('explorers.subtitle') }}
    </div>

    <v-select
      v-model="selection"
      class="mt-4"
      outlined
      :items="supportedExplorers"
      :label="$t('explorers.chain_selector')"
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
      :label="$t('explorers.address')"
      :hint="$t('explorers.address_url', { addressUrl })"
      :placeholder="addressUrl"
      persistent-hint
      @click:clear="saveAddress()"
    >
      <template #append-outer>
        <v-btn
          icon
          :disabled="!isValid(address)"
          class="pb-3"
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
      :label="$t('explorers.tx')"
      :hint="$t('explorers.tx_url', { txUrl })"
      :placeholder="txUrl"
      persistent-hint
      @click:clear="saveTransaction()"
    >
      <template #append-outer>
        <v-btn
          icon
          :disabled="!isValid(tx)"
          class="pb-3"
          @click="saveTransaction(tx)"
        >
          <v-icon>mdi-content-save</v-icon>
        </v-btn>
      </template>
    </v-text-field>
  </div>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Component, Mixins } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { explorerUrls } from '@/components/helper/asset-urls';
import SettingsMixin from '@/mixins/settings-mixin';
import { ExplorersSettings } from '@/types/frontend-settings';

const ETC = 'ETC' as const;

@Component({
  computed: {
    ...mapState('settings', ['explorers'])
  }
})
export default class Explorers extends Mixins(SettingsMixin) {
  readonly supportedExplorers = [...Object.values(Blockchain), ETC];
  selection: Blockchain | typeof ETC = Blockchain.ETH;
  explorers!: ExplorersSettings;

  address: string = '';
  tx: string = '';

  get txUrl(): string {
    const setting = this.explorers[this.selection];
    return setting?.transaction ?? explorerUrls[this.selection].transaction;
  }

  get addressUrl(): string {
    const setting = this.explorers[this.selection];
    return setting?.address ?? explorerUrls[this.selection].address;
  }

  onChange() {
    const setting = this.explorers[this.selection];
    this.address = setting?.address ?? '';
    this.tx = setting?.transaction ?? '';
  }

  mounted() {
    this.onChange();
  }

  isValid(entry: string | null): boolean {
    return !entry ? false : entry.length > 0;
  }

  saveAddress(address?: string) {
    this.address = address ?? '';
    const setting = this.explorers[this.selection];

    const updated = {
      ...setting,
      address: address
    };

    if (!address) {
      delete updated.address;
    }

    this.updateSetting({
      explorers: {
        ...this.explorers,
        [this.selection]: updated
      }
    });
  }

  saveTransaction(transaction?: string) {
    const setting = this.explorers[this.selection];

    const updated = {
      ...setting,
      transaction: transaction
    };

    if (!transaction) {
      delete updated.transaction;
    }

    this.updateSetting({
      explorers: {
        ...this.explorers,
        [this.selection]: updated
      }
    });
  }
}
</script>

<style scoped lang="scss">
.explorers {
  ::v-deep {
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
