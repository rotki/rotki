<template>
  <fragment>
    <v-form :value="value" class="pt-2" @input="input">
      <v-row>
        <v-col cols="12" md="4" xl="2">
          <v-select
            v-model="assetType"
            outlined
            :label="$t('asset_form.labels.asset_type')"
            disabled
            :items="types"
          />
        </v-col>

        <v-col>
          <v-text-field
            v-model="address"
            outlined
            :error-messages="errors['address']"
            :label="$t('asset_form.labels.address')"
            :disabled="saving"
            @focus="delete errors['address']"
          />
        </v-col>
      </v-row>
      <v-text-field
        v-model="name"
        outlined
        :error-messages="errors['name']"
        :label="$t('asset_form.labels.name')"
        :disabled="saving"
        @focus="delete errors['name']"
      />
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="symbol"
            outlined
            :error-messages="errors['symbol']"
            :label="$t('asset_form.labels.symbol')"
            :disabled="saving"
            @focus="delete errors['symbol']"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="decimals"
            type="number"
            outlined
            min="0"
            max="18"
            :label="$t('asset_form.labels.decimals')"
            :error-messages="errors['decimals']"
            :disabled="saving"
            @focus="delete errors['decimals']"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="coingecko"
            outlined
            clearable
            persistent-hint
            :hint="$t('asset_form.labels.coingecko_hint')"
            :label="$t('asset_form.labels.coingecko')"
            :error-messages="errors['coingecko']"
            :disabled="saving"
            @focus="delete errors['coingecko']"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="cryptocompare"
            outlined
            persistent-hint
            clearable
            :label="$t('asset_form.labels.cryptocompare')"
            :hint="$t('asset_form.labels.cryptocompare_hint')"
            :error-messages="errors['cryptocompare']"
            :disabled="saving"
            @focus="delete errors['cryptocompare']"
          />
        </v-col>
      </v-row>
    </v-form>

    <v-sheet outlined rounded class="mt-2">
      <v-expansion-panels flat tile>
        <v-expansion-panel>
          <v-expansion-panel-header>
            {{ $t('asset_form.optional') }}
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <date-time-picker
              v-model="started"
              seconds
              outlined
              :label="$t('asset_form.labels.started')"
              :error-messages="errors['started']"
              :disabled="saving"
              @focus="delete errors['started']"
            />
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="protocol"
                  outlined
                  persistent-hint
                  clearable
                  clear-icon="mdi-close"
                  class="asset-form__protocol"
                  :label="$t('asset_form.labels.protocol')"
                  :error-messages="errors['protocol']"
                  :disabled="saving"
                  @focus="delete errors['protocol']"
                />
              </v-col>
              <v-col cols="12" md="6">
                <asset-select
                  v-model="swappedFor"
                  outlined
                  persistent-hint
                  clearable
                  :label="$t('asset_form.labels.swapped_for')"
                  :error-messages="errors['swapped_for']"
                  :disabled="saving"
                  @focus="delete errors['swapped_for']"
                />
              </v-col>
            </v-row>
            <underlying-token-manager v-model="underlyingTokens" />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-sheet>

    <v-row class="mt-4">
      <v-col cols="auto">
        <v-sheet outlined rounded class="asset-form__icon">
          <crypto-icon
            v-if="preview"
            :symbol="preview"
            size="72px"
            changeable
            @status-change="forceSymbol = $event"
          />
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
  </fragment>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import UnderlyingTokenManager from '@/components/asset-manager/UnderlyingTokenManager.vue';
import Fragment from '@/components/helper/Fragment';
import RowActions from '@/components/helper/RowActions.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import { CustomEthereumToken, UnderlyingToken } from '@/services/assets/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { showError } from '@/store/utils';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

@Component({
  components: {
    Fragment,
    UnderlyingTokenManager,
    RowActions,
    FileUpload
  },
  methods: { ...mapActions('balances', ['fetchSupportedAssets']) }
})
export default class AssetForm extends Vue {
  address: string = '';
  name: string = '';
  symbol: string = '';
  decimals: string = '';
  started: string = '';
  coingecko: string = '';
  cryptocompare: string = '';
  assetType: string = 'Ethereum token';
  types: string[] = ['Ethereum token'];
  identifier: string = '';
  protocol: string = '';
  swappedFor: string = '';
  fetchSupportedAssets!: (refresh: boolean) => Promise<void>;

  underlyingTokens: UnderlyingToken[] = [];
  icon: File | null = null;

  errors: { [key: string]: string[] } = {};
  forceSymbol = false;

  @Prop({ required: true, type: Boolean })
  value!: boolean;

  @Prop({ required: false, default: () => null })
  edit!: CustomEthereumToken | null;
  @Prop({ required: false, type: Boolean, default: false })
  saving!: boolean;

  @Emit()
  input(_value: boolean) {}

  get preview(): string | null {
    if (this.forceSymbol) {
      return this.symbol ?? null;
    }
    return this.identifier ?? this.symbol ?? null;
  }

  get token(): CustomEthereumToken {
    return {
      address: this.address,
      name: this.name,
      symbol: this.symbol,
      decimals: parseInt(this.decimals),
      coingecko: this.coingecko ? this.coingecko : undefined,
      cryptocompare: this.cryptocompare ? this.cryptocompare : undefined,
      started: this.started ? convertToTimestamp(this.started) : undefined,
      underlyingTokens:
        this.underlyingTokens.length > 0 ? this.underlyingTokens : undefined,
      swappedFor: this.swappedFor ? this.swappedFor : undefined,
      protocol: this.protocol ? this.protocol : undefined
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
    this.decimals = token.decimals ? token.decimals.toString() : '';
    this.started = token.started
      ? convertFromTimestamp(token.started, true)
      : '';
    this.coingecko = token.coingecko ?? '';
    this.cryptocompare = token.cryptocompare ?? '';
    this.underlyingTokens = token.underlyingTokens ?? [];
    this.identifier = token.identifier ?? '';
    this.swappedFor = token.swappedFor ?? '';
    this.protocol = token.protocol ?? '';
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
      this.identifier = identifier;
      await this.saveIcon(identifier);
      await this.fetchSupportedAssets(true);
      return true;
    } catch (e) {
      const message = deserializeApiErrorMessage(e.message) as any;
      if (!message) {
        showError(
          e.message,
          this.$t('asset_form.underlying_tokens').toString()
        );
      } else {
        const token = message.token;
        this.errors = token;
        const underlyingTokens = token.underlying_tokens;
        if (underlyingTokens) {
          const messages: string[] = [];
          for (const underlyingToken of Object.values(underlyingTokens)) {
            const ut = underlyingToken as any;
            if (ut.address) {
              messages.push(...(ut.address as string[]));
            }
            if (underlyingTokens.weight) {
              messages.push(...(ut.weight as string[]));
            }
          }

          showError(
            messages.join(','),
            this.$t('asset_form.underlying_tokens').toString()
          );
        } else if (token._schema) {
          showError(
            token._schema[0],
            this.$t('asset_form.underlying_tokens').toString()
          );
        }
      }

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

  &__protocol {
    ::v-deep {
      .v-text-field {
        &__slot {
          height: 60px;
        }
      }
    }
  }
}
</style>
