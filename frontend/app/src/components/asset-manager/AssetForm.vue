<template>
  <v-form :value="value" class="pt-2" @input="input">
    <v-text-field
      v-model="address"
      outlined
      :label="$t('asset_form.labels.address')"
    />
    <v-text-field
      v-model="name"
      outlined
      :label="$t('asset_form.labels.name')"
    />
    <v-row>
      <v-col cols="12" md="6">
        <v-text-field
          v-model="symbol"
          outlined
          :label="$t('asset_form.labels.symbol')"
        />
      </v-col>
      <v-col cols="12" md="6">
        <v-text-field
          v-model="decimals"
          type="number"
          outlined
          :label="$t('asset_form.labels.decimals')"
        />
      </v-col>
    </v-row>
    <date-time-picker
      v-model="started"
      seconds
      outlined
      :label="$t('asset_form.labels.started')"
    />
    <v-row>
      <v-col>
        <v-text-field
          v-model="coingecko"
          outlined
          :hint="$t('asset_form.labels.coingecko_hint')"
          :label="$t('asset_form.labels.coingecko')"
        />
      </v-col>
      <v-col>
        <v-text-field
          v-model="cryptocompare"
          outlined
          :label="$t('asset_form.labels.cryptocompare')"
          :hint="$t('asset_form.labels.cryptocompare_hint')"
        />
      </v-col>
    </v-row>
    <underlying-token-manager v-model="underlyingTokens" />
    <v-row class="mt-4">
      <v-col cols="auto">
        <v-sheet outlined rounded class="asset-form__icon">
          <crypto-icon v-if="!!symbol" :symbol="symbol" size="72" />
        </v-sheet>
      </v-col>
      <v-col>
        <file-upload
          source="icon"
          file-filter="image/*"
          @selected="icon = $event"
        />
      </v-col>
    </v-row>
    <v-row v-if="icon">
      <v-col class="text-caption">
        {{ $t('asset_form.replaced', { name: icon.name }) }}
      </v-col>
    </v-row>
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import UnderlyingTokenManager from '@/components/asset-manager/UnderlyingTokenManager.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RowActions from '@/components/helper/RowActions.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import { UnderlyingToken, CustomEthereumToken } from '@/services/assets/types';
import { showError } from '@/store/utils';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

@Component({
  components: {
    UnderlyingTokenManager,
    RowActions,
    FileUpload,
    BigDialog
  }
})
export default class AssetForm extends Vue {
  address: string = '';
  name: string = '';
  symbol: string = '';
  decimals: string = '';
  started: string = '';
  coingecko: string = '';
  cryptocompare: string = '';

  underlyingTokens: UnderlyingToken[] = [];
  icon: File | null = null;

  @Prop({ required: true, type: Boolean })
  value!: boolean;

  @Prop({ required: false, default: () => null })
  edit!: CustomEthereumToken | null;

  @Emit()
  input(_value: boolean) {}

  get token(): CustomEthereumToken {
    return {
      address: this.address,
      name: this.name,
      symbol: this.symbol,
      decimals: parseInt(this.decimals),
      coingecko: this.coingecko,
      cryptocompare: this.cryptocompare,
      started: convertToTimestamp(this.started),
      underlyingTokens:
        this.underlyingTokens.length > 0 ? this.underlyingTokens : undefined
    };
  }

  mounted() {
    const token = this.edit;
    if (!token) {
      return;
    }
    this.address = token.address;
    this.name = token.name;
    this.symbol = token.symbol;
    this.decimals = token.decimals.toString();
    this.started = convertFromTimestamp(token.started, true);
    this.coingecko = token.coingecko;
    this.cryptocompare = token.cryptocompare;
    this.underlyingTokens = token.underlyingTokens ?? [];
  }

  async saveIcon(identifier: string) {
    if (!this.icon) {
      return;
    }

    let success = false;
    let message = '';
    try {
      if (this.$interop.isPackaged) {
        await this.$api.assets.setIcon(identifier, this.icon.path);
      } else {
        await this.$api.assets.uploadIcon(identifier, this.icon);
      }
      success = true;
    } catch (e) {
      message = e.message;
    }

    if (!success) {
      showError(
        this.$t('asset_form.icon_upload.description', {
          message
        }).toString(),
        this.$t('asset_form.icon_upload.title').toString()
      );
    }
  }

  async save(): Promise<boolean> {
    try {
      const token = this.token!;
      let identifier: string;
      if (this.edit) {
        ({ identifier } = await this.$api.assets.editCustomToken(token));
      } else {
        ({ identifier } = await this.$api.assets.addCustomToken(token));
      }
      await this.saveIcon(identifier);
      return true;
    } catch (e) {
      return false;
    }
  }
}
</script>

<style scoped lang="scss">
.asset-form {
  &__icon {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    width: 96px;
    height: 100%;
  }
}
</style>
