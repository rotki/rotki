<script setup lang="ts">
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { decimalsTextModel } from '@/modules/assets/admin/asset-field-models';
import { solanaTokenMigrationSchema } from '@/modules/assets/admin/solana-token-migration/solana-token-migration-form';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { solanaTokenKindsData } from '@/modules/core/common/chains';
import { useModelForm } from '@/modules/core/form/use-model-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

interface SolanaTokenMigrationData {
  address: string;
  decimals: number | null;
  tokenKind: string;
}

const modelValue = defineModel<SolanaTokenMigrationData>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { loading, oldAsset } = defineProps<{
  loading?: boolean;
  oldAsset?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { getAssetInfo } = useAssetInfoRetrieval();

const schema = computed<ZodType>(() => solanaTokenMigrationSchema({
  addressInvalid: t('asset_management.solana_token_migration.validation.address_invalid'),
  addressMissing: t('asset_management.solana_token_migration.validation.address_non_empty'),
  decimalsMissing: t('asset_management.solana_token_migration.validation.decimals_non_empty'),
  tokenKindMissing: t('asset_management.solana_token_migration.validation.token_kind_non_empty'),
}));

const form = useModelForm<SolanaTokenMigrationData>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
});

/** The asset being migrated as a heading and a name under it; an unknown one is its identifier alone. */
const migrating = computed<{ title: string; name?: string } | undefined>(() => {
  if (!oldAsset) {
    return undefined;
  }
  const details = getAssetInfo(oldAsset);

  if (!details) {
    return { title: oldAsset };
  }

  if (details.symbol)
    return { name: details.name ?? undefined, title: details.symbol };

  return { title: details.name ?? oldAsset };
});

const decimalsModel = decimalsTextModel(
  toRef(form.state, 'decimals'),
  () => form.touch('decimals'),
);

function clearFieldError(field: keyof SolanaTokenMigrationData) {
  const currentErrors = get(errors);
  if (currentErrors[field]) {
    const { [field]: _, ...rest } = currentErrors;
    set(errors, rest);
  }
}

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <dl
      v-if="oldAsset && migrating"
      class="m-0 flex flex-col gap-1 rounded-rui-control border border-rui-divider px-4 py-3"
      data-testid="solana-migration-summary"
    >
      <dt class="text-sm font-medium text-rui-text-secondary">
        {{ t('asset_management.solana_token_migration.migrating_asset') }}
      </dt>
      <dd class="m-0 flex flex-col">
        <span class="font-medium text-rui-text">
          {{ migrating.title }}
          <span
            v-if="migrating.name"
            class="font-normal text-rui-text-secondary"
          >
            {{ migrating.name }}
          </span>
        </span>
        <span
          v-if="migrating.title !== oldAsset"
          class="font-mono text-xs text-rui-text-secondary break-all"
        >
          {{ oldAsset }}
        </span>
      </dd>
    </dl>

    <div class="grid grid-cols-2 gap-4">
      <div
        class="col-span-2"
        data-testid="address-input"
      >
        <RuiTextField
          v-model="form.state.address"
          color="primary"
          :error-messages="form.errors('address')"
          :label="t('asset_management.solana_token_migration.solana_address')"
          :disabled="loading"
          @update:model-value="form.touch('address')"
          @input="clearFieldError('address')"
        />
      </div>

      <div
        class="col-span-2 md:col-span-1"
        data-testid="decimals-input"
      >
        <AmountInput
          v-model="decimalsModel"
          color="primary"
          integer
          :label="t('asset_form.labels.decimals')"
          :error-messages="form.errors('decimals')"
          :disabled="loading"
          @input="clearFieldError('decimals')"
        />
      </div>

      <div
        class="col-span-2 md:col-span-1"
        data-testid="token-kind-select"
      >
        <RuiMenuSelect
          v-model="form.state.tokenKind"
          :label="t('asset_form.labels.token_kind')"
          :options="solanaTokenKindsData"
          :error-messages="form.errors('tokenKind')"
          :disabled="loading"
          key-attr="identifier"
          text-attr="label"
          @update:model-value="form.touch('tokenKind'); clearFieldError('tokenKind')"
        />
      </div>
    </div>
  </div>
</template>
