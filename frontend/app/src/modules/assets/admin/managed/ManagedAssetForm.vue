<script setup lang="ts">
import type { SupportedAsset, UnderlyingToken } from '@rotki/common';
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { decimalsTextModel, startedEpochModel } from '@/modules/assets/admin/asset-field-models';
import AssetIconForm from '@/modules/assets/admin/AssetIconForm.vue';
import { toAssetTypeOptions, useAssetKind } from '@/modules/assets/admin/managed/asset-kind';
import {
  type ManagedAssetFormState,
  managedAssetSchema,
  toManagedAssetFormState,
} from '@/modules/assets/admin/managed/managed-asset-form';
import ManagedAssetOracleFields from '@/modules/assets/admin/managed/ManagedAssetOracleFields.vue';
import { useManagedAssetErrors } from '@/modules/assets/admin/managed/use-managed-asset-errors';
import { useManagedAssetSave } from '@/modules/assets/admin/managed/use-managed-asset-save';
import { useManagedTokenLookup } from '@/modules/assets/admin/managed/use-managed-token-lookup';
import UnderlyingTokenManager from '@/modules/assets/admin/UnderlyingTokenManager.vue';
import { evmTokenKindsData, solanaTokenKindsData } from '@/modules/core/common/chains';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useMappedModelForm } from '@/modules/core/form/use-model-form';
import CopyButton from '@/modules/shell/components/CopyButton.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

const modelValue = defineModel<SupportedAsset>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { editMode = false, assetTypes } = defineProps<{
  editMode?: boolean;
  loading?: boolean;
  assetTypes: string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const underlyingTokens = ref<UnderlyingToken[]>([]);
const assetIconFormRef = useTemplateRef<InstanceType<typeof AssetIconForm>>('assetIconFormRef');

const { allEvmChains } = useSupportedChains();

const identifier = computed<string>(() => get(modelValue).identifier);

const {
  isEvmToken,
  isHyperliquidToken,
  isNft,
  isSolanaToken,
  requiresAddress: isTokenRequiresAddress,
} = useAssetKind(() => get(modelValue).assetType, () => get(modelValue).tokenKind);

const { saveAsset } = useManagedAssetSave({
  asset: modelValue,
  editMode: () => editMode,
  underlyingTokens,
});

const { clearFields } = useManagedAssetErrors(errors, () => get(modelValue).assetType);

const schema = computed<ZodType>(() => managedAssetSchema({
  addressInvalid: t('asset_form.validation.valid_address'),
  addressMissing: t('asset_form.validation.address_non_empty'),
  assetTypeMissing: t('asset_form.validation.asset_type_non_empty'),
  collectibleIdMissing: t('asset_form.validation.collectible_id_non_empty'),
}, {
  isNft: get(isNft),
  requiresAddress: get(isTokenRequiresAddress),
}));

const form = useMappedModelForm<SupportedAsset, ManagedAssetFormState>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
  toModel: (state, asset): SupportedAsset => ({ ...asset, ...state }),
  toState: toManagedAssetFormState,
});

const startedModel = startedEpochModel(toRef(form.state, 'started'));
const decimalsModel = decimalsTextModel(toRef(form.state, 'decimals'));

const { fetching, refreshTokenData, suppressNextLookup } = useManagedTokenLookup({
  address: () => form.state.address,
  asset: modelValue,
  evmChain: () => get(modelValue).evmChain,
  onFilled: clearFields,
});

function saveIcon(identifier: string) {
  get(assetIconFormRef)?.saveIcon(identifier);
}

const types = computed<ReturnType<typeof toAssetTypeOptions>>(() => toAssetTypeOptions(assetTypes));

watchImmediate(modelValue, (asset: SupportedAsset) => {
  if (asset.underlyingTokens && asset.underlyingTokens.length > 0) {
    set(underlyingTokens, asset.underlyingTokens);
  }
  else {
    set(underlyingTokens, []);
  }
});

onMounted(() => {
  // An opened edit dialog seeds the address it already has, which must not read as a fresh one.
  if (editMode)
    suppressNextLookup();
});

defineExpose({
  saveAsset,
  saveIcon,
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-3">
    <div
      v-if="editMode"
      class="flex items-center text-caption text-rui-text-secondary -mt-2 mb-4 gap-2"
    >
      <span class="font-medium"> {{ t('asset_form.identifier') }}: </span>
      <div class="flex items-center">
        {{ identifier }}
        <CopyButton
          class="ml-2"
          size="sm"
          :value="identifier"
          :tooltip="t('asset_form.identifier_copy')"
        />
      </div>
    </div>
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-3">
      <div
        class="col-span-2"
        data-testid="type-select"
      >
        <RuiMenuSelect
          v-model="form.state.assetType"
          :label="t('asset_form.labels.asset_type')"
          :options="types"
          :disabled="types.length === 1 || editMode"
          :error-messages="form.errors('assetType')"
          key-attr="key"
          text-attr="label"
          variant="outlined"
        />
      </div>

      <template v-if="isEvmToken">
        <div data-testid="chain-select">
          <RuiAutoComplete
            v-model="form.state.evmChain"
            :label="t('asset_form.labels.chain')"
            :options="allEvmChains"
            :disabled="editMode"
            :error-messages="form.errors('evmChain')"
            auto-select-first
            key-attr="name"
            text-attr="label"
            variant="outlined"
          >
            <template #selection="{ item }">
              <ChainDisplay
                evm-chain
                :chain="item.name"
              />
            </template>
            <template #item="{ item }">
              <ChainDisplay
                evm-chain
                :chain="item.name"
              />
            </template>
          </RuiAutoComplete>
        </div>

        <div data-testid="token-select">
          <RuiMenuSelect
            v-model="form.state.tokenKind"
            :label="t('asset_form.labels.token_kind')"
            :options="evmTokenKindsData"
            :disabled="editMode"
            :error-messages="form.errors('tokenKind')"
            key-attr="identifier"
            text-attr="label"
            variant="outlined"
          />
        </div>
        <div
          class="col-span-2 flex flex-col sm:flex-row gap-3"
          data-testid="address-input"
        >
          <RuiTextField
            v-model="form.state.address"
            class="flex-1"
            variant="outlined"
            color="primary"
            :loading="fetching"
            :error-messages="form.errors('address')"
            :label="t('common.address')"
            :disabled="loading || fetching || editMode"
            @update:model-value="form.touch('address')"
          >
            <template
              v-if="editMode"
              #append
            >
              <RuiButton
                variant="text"
                icon
                :disabled="loading || fetching"
                @click="refreshTokenData()"
              >
                <RuiIcon name="lu-refresh-cw" />
              </RuiButton>
            </template>
          </RuiTextField>

          <RuiTextField
            v-if="isNft"
            v-model="form.state.collectibleId"
            data-testid="collectible-id-input"
            class="sm:w-1/4"
            variant="outlined"
            color="primary"
            type="number"
            :label="t('asset_form.labels.collectible_id')"
            :error-messages="form.errors('collectibleId')"
            :disabled="loading || editMode"
          />
        </div>
      </template>

      <template v-else-if="isSolanaToken">
        <div
          class="col-span-2"
          data-testid="token-select"
        >
          <RuiMenuSelect
            v-model="form.state.tokenKind"
            :label="t('asset_form.labels.token_kind')"
            :options="solanaTokenKindsData"
            :disabled="editMode"
            :error-messages="form.errors('tokenKind')"
            key-attr="identifier"
            text-attr="label"
            variant="outlined"
          />
        </div>
        <div
          class="col-span-2"
          data-testid="address-input"
        >
          <RuiTextField
            v-model="form.state.address"
            variant="outlined"
            color="primary"
            :loading="fetching"
            :error-messages="form.errors('address')"
            :label="t('common.address')"
            :disabled="loading || fetching || editMode"
            @update:model-value="form.touch('address')"
          />
        </div>
      </template>

      <div
        v-else-if="isHyperliquidToken"
        class="col-span-2"
        data-testid="address-input"
      >
        <RuiTextField
          v-model="form.state.address"
          variant="outlined"
          color="primary"
          :error-messages="form.errors('address')"
          :label="t('common.address')"
          :disabled="loading || editMode"
          @update:model-value="form.touch('address')"
        />
      </div>

      <div class="col-span-2 grid md:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-3">
        <RuiTextField
          v-model="form.state.name"
          data-testid="name-input"
          class="md:col-span-2"
          variant="outlined"
          color="primary"
          :error-messages="form.errors('name')"
          :label="t('common.name')"
          :disabled="loading || fetching"
          @update:model-value="form.touch('name')"
        />

        <RuiTextField
          v-model="form.state.symbol"
          :class="isTokenRequiresAddress ? 'md:col-span-1' : 'md:col-span-2'"
          data-testid="symbol-input"
          variant="outlined"
          color="primary"
          :error-messages="form.errors('symbol')"
          :label="t('asset_form.labels.symbol')"
          :disabled="loading || fetching"
          @update:model-value="form.touch('symbol')"
        />
        <div
          v-if="isTokenRequiresAddress"
          data-testid="decimal-input"
        >
          <RuiTextField
            v-model="decimalsModel"
            variant="outlined"
            color="primary"
            min="0"
            max="18"
            type="number"
            :label="t('asset_form.labels.decimals')"
            :error-messages="form.errors('decimals')"
            :disabled="loading || fetching"
            @update:model-value="form.touch('decimals')"
          />
        </div>
        <ManagedAssetOracleFields
          v-model:coingecko="form.state.coingecko"
          v-model:cryptocompare="form.state.cryptocompare"
          :coingecko-errors="form.errors('coingecko')"
          :cryptocompare-errors="form.errors('cryptocompare')"
          :disabled="loading"
          @touch="form.touch($event)"
        />
      </div>
    </div>

    <RuiCard
      no-padding
      rounded="sm"
      class="col-span-2 mt-2 mb-4 overflow-hidden"
    >
      <RuiAccordions>
        <RuiAccordion
          header-grow
          :class-names="{ header: 'p-4' }"
        >
          <template #header>
            {{ t('asset_form.optional') }}
          </template>
          <template #default>
            <div class="p-4">
              <DateTimePicker
                v-model="startedModel"
                variant="outlined"
                :label="t('asset_form.labels.started')"
                :error-messages="form.errors('started')"
                type="epoch"
                :disabled="loading"
              />
              <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
                <RuiTextField
                  v-if="isEvmToken"
                  v-model="form.state.protocol"
                  variant="outlined"
                  color="primary"
                  clearable
                  :label="t('common.protocol')"
                  :error-messages="form.errors('protocol')"
                  :disabled="loading"
                  @update:model-value="form.touch('protocol')"
                />
                <AssetSelect
                  v-model="form.state.swappedFor"
                  variant="outlined"
                  clearable
                  :label="t('asset_form.labels.swapped_for')"
                  :error-messages="form.errors('swappedFor')"
                  :disabled="loading"
                />
                <AssetSelect
                  v-if="!isEvmToken && form.state.assetType"
                  v-model="form.state.forked"
                  variant="outlined"
                  clearable
                  :label="t('asset_form.labels.forked')"
                  :error-messages="form.errors('forked')"
                  :disabled="loading"
                />
                <RuiSwitch
                  v-if="isEvmToken && !isNft"
                  v-model="form.state.isRebasing"
                  class="md:col-span-2"
                  :disabled="loading"
                  :hint="t('asset_form.labels.rebasing_hint')"
                >
                  {{ t('asset_form.labels.rebasing') }}
                </RuiSwitch>
              </div>
              <UnderlyingTokenManager
                v-if="isEvmToken"
                v-model="underlyingTokens"
                class="border-t border-default pt-6 mt-2"
              />
            </div>
          </template>
        </RuiAccordion>
      </RuiAccordions>
    </RuiCard>

    <AssetIconForm
      ref="assetIconFormRef"
      class="col-span-2"
      :identifier="identifier"
      refreshable
    />
  </div>
</template>
