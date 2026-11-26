import type { SupportedAsset } from '@rotki/common';
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { FormApi } from '@/modules/core/form/use-form';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, onMounted, type Ref, toRef, toValue, type UnwrapNestedRefs, type WritableComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { decimalsTextModel, startedEpochModel } from '@/modules/assets/admin/asset-field-models';
import { toAssetTypeOptions, useAssetKind } from '@/modules/assets/admin/managed/asset-kind';
import {
  type ManagedAssetFormState,
  managedAssetSchema,
  toManagedAssetFormState,
} from '@/modules/assets/admin/managed/managed-asset-form';
import { useManagedAssetErrors } from '@/modules/assets/admin/managed/use-managed-asset-errors';
import { useManagedTokenLookup } from '@/modules/assets/admin/managed/use-managed-token-lookup';
import { useMappedModelForm } from '@/modules/core/form/use-model-form';

interface ManagedAssetFormStateOptions {
  /** The asset the form edits. The form writes its edits back into it. */
  readonly modelValue: Ref<SupportedAsset>;
  /** The server's validation errors, shown on the fields and cleared when they stop applying. */
  readonly errors: Ref<ValidationErrors>;
  /** Raised once the user has edited the form, so the dialog can ask before discarding. */
  readonly stateUpdated: Ref<boolean>;
  /** Whether an existing asset is edited rather than a new one added. */
  readonly editMode: MaybeRefOrGetter<boolean>;
  /** The asset types the type select offers. */
  readonly assetTypes: MaybeRefOrGetter<string[]>;
}

interface ManagedAssetFormStateReturn {
  /** The form the inputs bind to. */
  readonly form: FormApi<ManagedAssetFormState, UnwrapNestedRefs<ManagedAssetFormState>>;
  /** The start date as the date picker holds it. */
  readonly startedModel: WritableComputedRef<number>;
  /** The decimals as the text input holds them. */
  readonly decimalsModel: WritableComputedRef<string>;
  readonly isEvmToken: ComputedRef<boolean>;
  readonly isHyperliquidToken: ComputedRef<boolean>;
  readonly isSolanaToken: ComputedRef<boolean>;
  /** A collectible. It has an id instead of decimals, and cannot rebase. */
  readonly isNft: ComputedRef<boolean>;
  /** The three token types that are identified by an on-chain address. */
  readonly isTokenRequiresAddress: ComputedRef<boolean>;
  /** The options of the asset type select. */
  readonly types: ComputedRef<ReturnType<typeof toAssetTypeOptions>>;
  /** True while a token lookup is in flight. */
  readonly fetching: Readonly<Ref<boolean>>;
  /** Looks the token up now, for the button that asks for it. */
  readonly refreshTokenData: () => Promise<void>;
}

/**
 * The managed asset form's fields: its validation, the inputs' bindings and the token lookup that
 * fills a pasted address in.
 */
export function useManagedAssetFormState(options: ManagedAssetFormStateOptions): ManagedAssetFormStateReturn {
  const { assetTypes, editMode, errors, modelValue, stateUpdated } = options;

  const { t } = useI18n({ useScope: 'global' });

  const {
    isEvmToken,
    isHyperliquidToken,
    isNft,
    isSolanaToken,
    requiresAddress: isTokenRequiresAddress,
  } = useAssetKind(() => get(modelValue).assetType, () => get(modelValue).tokenKind);

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

  const types = computed<ReturnType<typeof toAssetTypeOptions>>(() => toAssetTypeOptions(toValue(assetTypes)));

  /**
   * Stops the address the form opens with from triggering a lookup.
   *
   * @remarks
   * Only in edit mode, where the field is seeded from the asset being edited. That write looks the
   * same to the watcher as one the user made, and acting on it would overwrite the very fields the
   * dialog was opened to show.
   */
  function suppressLookupForSeededAddress(): void {
    if (toValue(editMode))
      suppressNextLookup();
  }

  onMounted(suppressLookupForSeededAddress);

  return {
    decimalsModel,
    fetching,
    form,
    isEvmToken,
    isHyperliquidToken,
    isNft,
    isSolanaToken,
    isTokenRequiresAddress,
    refreshTokenData,
    startedModel,
    types,
  };
}
