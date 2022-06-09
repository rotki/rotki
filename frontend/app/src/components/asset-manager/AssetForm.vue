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
          :tooltip="$tc('asset_form.identifier_copy')"
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
            :disabled="types.length === 1 || !!edit"
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
            @keydown.space.prevent
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
                :tooltip="$tc('asset_form.help_coingecko')"
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
                :tooltip="$tc('asset_form.help_cryptocompare')"
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
              :label="$tc('asset_form.labels.started')"
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
                  :label="$tc('asset_form.labels.swapped_for')"
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
                  :label="$tc('asset_form.labels.forked')"
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

    <div class="mb-4">
      <v-row class="mt-4">
        <v-col cols="auto">
          <v-sheet outlined rounded class="asset-form__icon">
            <v-tooltip v-if="preview" right>
              <template #activator="{ on }">
                <v-btn
                  fab
                  x-small
                  depressed
                  class="asset-form__icon__refresh"
                  color="primary"
                  :loading="refreshIconLoading"
                  v-on="on"
                  @click="refreshIcon"
                >
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </template>
              {{ $t('asset_form.fetch_latest_icon.title') }}
            </v-tooltip>

            <asset-icon
              v-if="preview"
              :identifier="preview"
              :symbol="symbol"
              size="72px"
              changeable
              :timestamp="timestamp"
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
    </div>
  </fragment>
</template>

<script lang="ts">
import { SupportedAsset } from '@rotki/common/lib/data';
import {
  computed,
  defineComponent,
  onBeforeMount,
  onMounted,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import UnderlyingTokenManager from '@/components/asset-manager/UnderlyingTokenManager.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import Fragment from '@/components/helper/Fragment';
import HelpLink from '@/components/helper/HelpLink.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import { setupGeneralBalances } from '@/composables/balances';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import {
  EthereumToken,
  ManagedAsset,
  UnderlyingToken
} from '@/services/assets/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import { useNotifications } from '@/store/notifications';
import { showError } from '@/store/utils';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

function value<T>(t: T): T | undefined {
  return t ? t : undefined;
}

function time(t: string): number | undefined {
  return t ? convertToTimestamp(t) : undefined;
}

const ETHEREUM_TOKEN = 'ethereum token';

export default defineComponent({
  name: 'AssetForm',
  components: {
    CopyButton,
    HelpLink,
    Fragment,
    UnderlyingTokenManager,
    FileUpload
  },
  props: {
    value: { required: true, type: Boolean },
    edit: {
      required: false,
      type: Object as PropType<ManagedAsset>,
      default: null
    },
    saving: { required: false, type: Boolean, default: false }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { edit } = toRefs(props);
    const { fetchSupportedAssets } = useAssetInfoRetrieval();
    const { fetchTokenDetails } = setupGeneralBalances();

    const input = (value: boolean) => {
      emit('input', value);
    };

    const address = ref<string>('');
    const name = ref<string>('');
    const symbol = ref<string>('');
    const decimals = ref<string>('');
    const started = ref<string>('');
    const coingecko = ref<string>('');
    const cryptocompare = ref<string>('');
    const assetType = ref<string>(ETHEREUM_TOKEN);
    const types = ref<string[]>([ETHEREUM_TOKEN]);
    const identifier = ref<string>('');
    const protocol = ref<string>('');
    const swappedFor = ref<string>('');
    const forked = ref<string>('');
    const coingeckoEnabled = ref<boolean>(false);
    const cryptocompareEnabled = ref<boolean>(false);
    const fetching = ref<boolean>(false);
    const dontAutoFetch = ref<boolean>(false);
    const refreshIconLoading = ref<boolean>(false);
    const timestamp = ref<number | null>(null);

    const underlyingTokens = ref<UnderlyingToken[]>([]);
    const icon = ref<File | null>(null);

    const errors = ref<{ [key: string]: string[] }>({});

    const isEthereumToken = computed<boolean>(() => {
      return get(assetType) === ETHEREUM_TOKEN;
    });

    const sanitizeAddress = (address: string) => {
      return address.replace(/\s/g, '');
    };

    watch(address, async () => {
      const sanitizedAddress = sanitizeAddress(get(address));
      if (get(address) !== sanitizedAddress) {
        set(address, sanitizedAddress);
        return;
      }

      if (
        get(dontAutoFetch) ||
        !get(address).startsWith('0x') ||
        get(address).length < 42
      ) {
        set(dontAutoFetch, false);
        return;
      }

      set(fetching, true);
      const {
        decimals: newDecimals,
        name: newName,
        symbol: newSymbol
      } = await fetchTokenDetails(get(address));
      set(decimals, newDecimals?.toString() || get(decimals));
      set(name, newName || get(name));
      set(symbol, newSymbol || get(symbol));
      set(fetching, false);
    });

    const preview = computed<string | null>(() => {
      return get(identifier) ?? get(symbol) ?? null;
    });

    const token = computed<Omit<EthereumToken, 'identifier'>>(() => {
      const ut = get(underlyingTokens);
      return {
        address: get(address),
        name: get(name),
        symbol: get(symbol),
        decimals: parseInt(get(decimals)),
        coingecko: get(coingeckoEnabled) ? value(get(coingecko)) : null,
        cryptocompare: get(cryptocompareEnabled)
          ? value(get(cryptocompare))
          : '',
        started: time(get(started)),
        underlyingTokens: ut.length > 0 ? ut : undefined,
        swappedFor: value(get(swappedFor)),
        protocol: value(get(protocol))
      };
    });

    const asset = computed<Omit<SupportedAsset, 'identifier'>>(() => {
      return {
        name: get(name),
        symbol: get(symbol),
        assetType: get(assetType),
        started: time(get(started)),
        forked: value(get(forked)),
        swappedFor: value(get(swappedFor)),
        coingecko: get(coingeckoEnabled) ? value(get(coingecko)) : null,
        cryptocompare: get(cryptocompareEnabled)
          ? value(get(cryptocompare))
          : ''
      };
    });

    onBeforeMount(async () => {
      try {
        set(types, await api.assets.assetTypes());
      } catch (e: any) {
        showError(
          i18n.t('asset_form.types.error', { message: e.message }).toString()
        );
      }
    });

    onMounted(() => {
      const token = get(edit);
      set(dontAutoFetch, !!get(edit));
      if (!token) {
        return;
      }

      set(name, token.name ?? '');
      set(symbol, token.symbol);
      set(identifier, token.identifier ?? '');
      set(swappedFor, token.swappedFor ?? '');
      set(
        started,
        token.started ? convertFromTimestamp(token.started, true) : ''
      );
      set(coingecko, token.coingecko ?? '');
      set(cryptocompare, token.cryptocompare ?? '');

      set(coingeckoEnabled, token.coingecko !== null);
      set(cryptocompareEnabled, token.cryptocompare !== '');

      if ('assetType' in token) {
        set(forked, token.forked ?? '');
        set(assetType, token.assetType);
      } else {
        set(address, token.address);
        set(decimals, token.decimals ? token.decimals.toString() : '');
        set(protocol, token.protocol ?? '');
        set(underlyingTokens, token.underlyingTokens ?? []);
        set(assetType, ETHEREUM_TOKEN);
      }
    });

    const saveIcon = async (identifier: string) => {
      if (!get(icon)) {
        return;
      }

      let success = false;
      let message = '';
      try {
        if (interop.appSession) {
          await api.assets.setIcon(identifier, get(icon)!.path);
        } else {
          await api.assets.uploadIcon(identifier, get(icon)!);
        }
        success = true;
      } catch (e: any) {
        message = e.message;
      }

      if (!success) {
        showError(
          i18n
            .t('asset_form.icon_upload.description', {
              message
            })
            .toString(),
          i18n.t('asset_form.icon_upload.title').toString()
        );
      }
    };

    const saveEthereumToken = async () => {
      let newIdentifier: string;
      const tokenVal = get(token)!;
      if (get(edit) && get(identifier)) {
        ({ identifier: newIdentifier } = await api.assets.editEthereumToken(
          tokenVal
        ));
      } else {
        ({ identifier: newIdentifier } = await api.assets.addEthereumToken(
          tokenVal
        ));
      }
      return newIdentifier;
    };

    const saveAsset = async () => {
      let newIdentifier: string;
      const assetVal = get(asset);
      if (get(edit)) {
        newIdentifier = get(identifier);
        await api.assets.editAsset({ ...assetVal, identifier: newIdentifier });
      } else {
        ({ identifier: newIdentifier } = await api.assets.addAsset(assetVal));
      }
      return newIdentifier;
    };

    const getUnderlyingTokenErrors = (underlyingTokens: any) => {
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
    };

    const handleError = (message: any) => {
      if (message.token) {
        const token = message.token;
        set(errors, token);
        const underlyingTokens = token.underlying_tokens;
        if (underlyingTokens) {
          const messages = getUnderlyingTokenErrors(underlyingTokens);

          showError(
            messages.join(','),
            i18n.t('asset_form.underlying_tokens').toString()
          );
        } else if (token._schema) {
          showError(
            token._schema[0],
            i18n.t('asset_form.underlying_tokens').toString()
          );
        }
      } else {
        set(errors, message);
      }
    };

    const save = async () => {
      try {
        const newIdentifier = get(isEthereumToken)
          ? await saveEthereumToken()
          : await saveAsset();
        set(identifier, newIdentifier);
        await saveIcon(newIdentifier);
        await fetchSupportedAssets(true);
        return true;
      } catch (e: any) {
        const message = deserializeApiErrorMessage(e.message) as any;
        if (!message) {
          showError(
            e.message,
            i18n.t('asset_form.underlying_tokens').toString()
          );
        } else {
          handleError(message);
        }

        return false;
      }
    };

    const { notify } = useNotifications();

    const refreshIcon = async () => {
      set(refreshIconLoading, true);
      const identifierVal = get(identifier);
      try {
        await api.assets.refreshIcon(identifierVal);
      } catch (e: any) {
        notify({
          title: i18n.tc('asset_form.fetch_latest_icon.title'),
          message: i18n.tc(
            'asset_form.fetch_latest_icon.description',
            undefined,
            {
              identifier: identifierVal,
              message: e.message
            }
          ),
          display: true
        });
      }
      set(refreshIconLoading, false);
      set(timestamp, Date.now());
    };

    return {
      address,
      name,
      symbol,
      decimals,
      started,
      coingecko,
      cryptocompare,
      assetType,
      types,
      identifier,
      protocol,
      swappedFor,
      forked,
      coingeckoEnabled,
      cryptocompareEnabled,
      fetching,
      dontAutoFetch,
      errors,
      underlyingTokens,
      preview,
      icon,
      input,
      isEthereumToken,
      save,
      refreshIcon,
      timestamp,
      refreshIconLoading
    };
  }
});
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
    position: relative;

    &__refresh {
      position: absolute;
      right: -1rem;
      top: -1rem;
    }
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
