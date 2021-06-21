<template>
  <fragment>
    <v-row
      v-if="!!edit"
      class="text-caption text--secondary py-2"
      align="center"
    >
      <v-col cols="auto" class="font-weight-medium">
        {{ $t('asset_form.identifier') }}
      </v-col>
      <v-col>
        {{ edit.identifier }}
        <copy-button
          :value="edit.identifier"
          :tooltip="$t('asset_form.identifier_copy')"
        />
      </v-col>
    </v-row>
    <v-form :value="value" class="pt-2" @input="input">
      <v-row>
        <v-col>
          <v-select
            v-model="assetType"
            outlined
            :label="$t('asset_form.labels.asset_type')"
            :disabled="types.length === 1"
            :items="types"
          />
        </v-col>
      </v-row>
      <v-row v-if="isEthereumToken">
        <v-col>
          <v-text-field
            v-model="address"
            outlined
            :loading="fetching"
            :error-messages="errors['address']"
            :label="$t('asset_form.labels.address')"
            :disabled="saving || fetching"
            @focus="delete errors['address']"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="name"
            outlined
            :error-messages="errors['name']"
            :label="$t('asset_form.labels.name')"
            :disabled="saving || fetching"
            @focus="delete errors['name']"
          />
        </v-col>
        <v-col cols="12" :md="isEthereumToken ? 3 : 6">
          <v-text-field
            v-model="symbol"
            outlined
            :error-messages="errors['symbol']"
            :label="$t('asset_form.labels.symbol')"
            :disabled="saving || fetching"
            @focus="delete errors['symbol']"
          />
        </v-col>
        <v-col v-if="isEthereumToken" cols="12" md="3">
          <v-text-field
            v-model="decimals"
            type="number"
            outlined
            min="0"
            max="18"
            :label="$t('asset_form.labels.decimals')"
            :error-messages="errors['decimals']"
            :disabled="saving || fetching"
            @focus="delete errors['decimals']"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6" class="d-flex flex-row">
          <v-text-field
            v-model="coingecko"
            outlined
            clearable
            persistent-hint
            :hint="$t('asset_form.labels.coingecko_hint')"
            :label="$t('asset_form.labels.coingecko')"
            :error-messages="errors['coingecko']"
            :disabled="saving || !coingeckoEnabled"
            @focus="delete errors['coingecko']"
          >
            <template #append>
              <help-link
                small
                :url="`${$interop.contributeUrl}#get-coingecko-asset-identifier`"
                :tooltip="$t('asset_form.help_coingecko')"
              />
            </template>
          </v-text-field>
          <v-tooltip open-delay="400" top max-width="320">
            <template #activator="{ attrs, on }">
              <span v-bind="attrs" v-on="on">
                <v-checkbox v-model="coingeckoEnabled" class="ms-4 me-2" />
              </span>
            </template>
            <span> {{ $t('asset_form.oracle_disable') }}</span>
          </v-tooltip>
        </v-col>
        <v-col cols="12" md="6" class="d-flex flex-row">
          <v-text-field
            v-model="cryptocompare"
            outlined
            persistent-hint
            clearable
            :label="$t('asset_form.labels.cryptocompare')"
            :hint="$t('asset_form.labels.cryptocompare_hint')"
            :error-messages="errors['cryptocompare']"
            :disabled="saving || !cryptocompareEnabled"
            @focus="delete errors['cryptocompare']"
          >
            <template #append>
              <help-link
                small
                :url="`${$interop.contributeUrl}#get-cryptocompare-asset-identifier`"
                :tooltip="$t('asset_form.help_cryptocompare')"
              />
            </template>
          </v-text-field>
          <v-tooltip open-delay="400" top max-width="320">
            <template #activator="{ attrs, on }">
              <span v-bind="attrs" v-on="on">
                <v-checkbox v-model="cryptocompareEnabled" class="ms-4 me-2" />
              </span>
            </template>
            <span> {{ $t('asset_form.oracle_disable') }}</span>
          </v-tooltip>
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
              <v-col v-if="isEthereumToken" cols="12" md="6">
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
              <v-col v-if="!isEthereumToken" cols="12" md="6">
                <asset-select
                  v-if="assetType"
                  v-model="forked"
                  outlined
                  persistent-hint
                  clearable
                  :label="$t('asset_form.labels.forked')"
                  :error-messages="errors['forked']"
                  :disabled="saving"
                  @focus="delete errors['forked']"
                />
              </v-col>
            </v-row>
            <underlying-token-manager
              v-if="isEthereumToken"
              v-model="underlyingTokens"
            />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-sheet>

    <v-row class="mt-4">
      <v-col cols="auto">
        <v-sheet outlined rounded class="asset-form__icon">
          <asset-icon
            v-if="preview"
            :identifier="preview"
            :symbol="symbol"
            size="72px"
            changeable
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
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import UnderlyingTokenManager from '@/components/asset-manager/UnderlyingTokenManager.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import Fragment from '@/components/helper/Fragment';
import HelpLink from '@/components/helper/HelpLink.vue';
import RowActions from '@/components/helper/RowActions.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import {
  EthereumToken,
  ManagedAsset,
  SupportedAsset,
  UnderlyingToken
} from '@/services/assets/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { ERC20Token } from '@/store/balances/types';
import { showError } from '@/store/utils';
import { Nullable } from '@/types';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

function value<T>(t: T): T | undefined {
  return t ? t : undefined;
}

function time(t: string): number | undefined {
  return t ? convertToTimestamp(t) : undefined;
}

const ETHEREUM_TOKEN = 'ethereum token';

@Component({
  components: {
    CopyButton,
    HelpLink,
    Fragment,
    UnderlyingTokenManager,
    RowActions,
    FileUpload
  },
  methods: {
    ...mapActions('balances', ['fetchSupportedAssets', 'fetchTokenDetails'])
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
  assetType: string = ETHEREUM_TOKEN;
  types: string[] = [ETHEREUM_TOKEN];
  identifier: string = '';
  protocol: string = '';
  swappedFor: string = '';
  forked: string = '';
  coingeckoEnabled: boolean = false;
  cryptocompareEnabled: boolean = false;
  fetchSupportedAssets!: (refresh: boolean) => Promise<void>;
  fetchTokenDetails!: (address: string) => Promise<ERC20Token>;
  fetching: boolean = false;
  dontAutoFetch: boolean = false;

  underlyingTokens: UnderlyingToken[] = [];
  icon: File | null = null;

  errors: { [key: string]: string[] } = {};

  @Prop({ required: true, type: Boolean })
  value!: boolean;

  @Prop({ required: false, default: () => null })
  edit!: Nullable<ManagedAsset>;
  @Prop({ required: false, type: Boolean, default: false })
  saving!: boolean;

  @Emit()
  input(_value: boolean) {}

  get isEthereumToken() {
    return this.assetType === ETHEREUM_TOKEN;
  }

  @Watch('address')
  async onAddressChange() {
    if (
      this.dontAutoFetch ||
      !this.address.startsWith('0x') ||
      this.address.length < 42
    ) {
      this.dontAutoFetch = false;
      return;
    }

    this.fetching = true;
    const { decimals, name, symbol } = await this.fetchTokenDetails(
      this.address
    );
    this.decimals = decimals?.toString() ?? '';
    this.name = name ?? '';
    this.symbol = symbol ?? '';
    this.fetching = false;
  }

  get preview(): string | null {
    return this.identifier ?? this.symbol ?? null;
  }

  get token(): Omit<EthereumToken, 'identifier'> {
    const ut = this.underlyingTokens;
    return {
      address: this.address,
      name: this.name,
      symbol: this.symbol,
      decimals: parseInt(this.decimals),
      coingecko: this.coingeckoEnabled ? value(this.coingecko) : null,
      cryptocompare: this.cryptocompareEnabled ? value(this.cryptocompare) : '',
      started: time(this.started),
      underlyingTokens: ut.length > 0 ? ut : undefined,
      swappedFor: value(this.swappedFor),
      protocol: value(this.protocol)
    };
  }

  get asset(): Omit<SupportedAsset, 'identifier'> {
    return {
      name: this.name,
      symbol: this.symbol,
      assetType: this.assetType,
      started: time(this.started),
      forked: value(this.forked),
      swappedFor: value(this.swappedFor),
      coingecko: this.coingeckoEnabled ? value(this.coingecko) : null,
      cryptocompare: this.cryptocompareEnabled ? value(this.cryptocompare) : ''
    };
  }

  async created() {
    try {
      this.types = await this.$api.assets.assetTypes();
    } catch (e) {
      showError(
        this.$t('asset_form.types.error', { message: e.message }).toString()
      );
    }
  }

  mounted() {
    const token = this.edit;
    this.dontAutoFetch = !!this.edit;
    if (!token) {
      return;
    }

    this.name = token.name;
    this.symbol = token.symbol;
    this.identifier = token.identifier ?? '';
    this.swappedFor = token.swappedFor ?? '';
    this.started = token.started
      ? convertFromTimestamp(token.started, true)
      : '';
    this.coingecko = token.coingecko ?? '';
    this.cryptocompare = token.cryptocompare ?? '';

    this.coingeckoEnabled = token.coingecko !== null;
    this.cryptocompareEnabled = token.cryptocompare !== '';

    if ('assetType' in token) {
      this.forked = token.forked ?? '';
      this.assetType = token.assetType;
    } else {
      this.address = token.address;
      this.decimals = token.decimals ? token.decimals.toString() : '';
      this.protocol = token.protocol ?? '';
      this.underlyingTokens = token.underlyingTokens ?? [];
      this.assetType = ETHEREUM_TOKEN;
    }
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
      const identifier = this.isEthereumToken
        ? await this.saveEthereumToken()
        : await this.saveAsset();
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
        this.handleError(message);
      }

      return false;
    }
  }

  private handleError(message: any) {
    if (message.token) {
      const token = message.token;
      this.errors = token;
      const underlyingTokens = token.underlying_tokens;
      if (underlyingTokens) {
        const messages = this.getUnderlyingTokenErrors(underlyingTokens);

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
    } else {
      this.errors = message;
    }
  }

  private getUnderlyingTokenErrors(underlyingTokens: any) {
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
    return messages;
  }

  private async saveEthereumToken() {
    let identifier: string;
    const token = this.token!;
    if (this.edit && this.identifier) {
      ({ identifier } = await this.$api.assets.editEthereumToken(token));
    } else {
      ({ identifier } = await this.$api.assets.addEthereumToken(token));
    }
    return identifier;
  }

  private async saveAsset() {
    let identifier: string;
    const asset = this.asset;
    if (this.edit) {
      identifier = this.identifier;
      await this.$api.assets.editAsset({ ...asset, identifier });
    } else {
      ({ identifier } = await this.$api.assets.addAsset(asset));
    }
    return identifier;
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
