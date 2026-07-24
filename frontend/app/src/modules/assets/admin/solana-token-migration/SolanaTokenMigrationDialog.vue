<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { useTemplateRef } from 'vue';
import { extractTargetAssetFromError, isUniqueConstraintError } from '@/modules/assets/admin/solana-token-migration/solana-migration-error';
import { useSolanaTokenMigrationApi } from '@/modules/assets/admin/solana-token-migration/solana-token-migration';
import { useSolanaTokenMigrationStore } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import SolanaTokenMigrationForm from './SolanaTokenMigrationForm.vue';

interface SolanaTokenMigrationData {
  address: string;
  decimals: number | null;
  tokenKind: string;
}

const modelValue = defineModel<SolanaTokenMigrationData | undefined>({ required: true });
const oldAsset = defineModel<string | undefined>('oldAsset', { required: false });

const emit = defineEmits<{
  'refresh': [];
  'suggest-merge': [event: { sourceAsset: string; targetAsset: string }];
}>();

const { t } = useI18n({ useScope: 'global' });

const loading = ref(false);
const errorMessages = ref<ValidationErrors>({});
const form = useTemplateRef<InstanceType<typeof SolanaTokenMigrationForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { removeIdentifier } = useSolanaTokenMigrationStore();
const { migrateSolanaToken } = useSolanaTokenMigrationApi();

async function save(): Promise<boolean> {
  if (!isDefined(modelValue) || !isDefined(oldAsset))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  const assetToMigrate = get(oldAsset);

  if (!data.decimals || !assetToMigrate) {
    setMessage({
      description: t('asset_management.solana_token_migration.validation_error'),
      title: t('asset_management.solana_token_migration.dialog_title'),
    });
    return false;
  }

  set(loading, true);

  try {
    const result = await migrateSolanaToken({
      address: data.address,
      decimals: data.decimals,
      oldAsset: assetToMigrate,
      tokenKind: data.tokenKind,
    });

    if (result) {
      removeIdentifier(assetToMigrate);

      setMessage({
        description: t('asset_management.solana_token_migration.migration_success'),
        success: true,
        title: t('asset_management.solana_token_migration.dialog_title'),
      });

      set(modelValue, undefined);
      set(oldAsset, undefined);
      emit('refresh');
      return true;
    }
    else {
      setMessage({
        description: t('asset_management.solana_token_migration.migration_error'),
        title: t('asset_management.solana_token_migration.dialog_title'),
      });
      return false;
    }
  }
  catch (error: unknown) {
    return handleSaveException(error, assetToMigrate, formRef);
  }
  finally {
    set(loading, false);
  }
}

type MigrationFormRef = InstanceType<typeof SolanaTokenMigrationForm> | null | undefined;

// Suggests a merge for a unique-constraint conflict; returns true when handled.
function suggestMergeOnConflict(message: string, assetToMigrate: string): boolean {
  if (!isUniqueConstraintError(message))
    return false;

  const targetAsset = extractTargetAssetFromError(message);
  if (!targetAsset)
    return false;

  emit('suggest-merge', { sourceAsset: assetToMigrate, targetAsset });
  set(modelValue, undefined);
  set(oldAsset, undefined);
  return true;
}

function handleSaveException(error: unknown, assetToMigrate: string, formRef: MigrationFormRef): boolean {
  let errors: ValidationErrors | string = getErrorMessage(error);
  if (error instanceof ApiValidationError)
    errors = error.getValidationErrors({});

  if (typeof errors === 'string') {
    if (suggestMergeOnConflict(errors, assetToMigrate))
      return false;

    setMessage({
      description: errors,
      title: t('asset_management.solana_token_migration.migration_error'),
    });
  }
  else {
    set(errorMessages, errors);
    formRef?.validate();
  }
  return false;
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="t('asset_management.solana_token_migration.dialog_title')"
    :primary-action="t('asset_management.solana_token_migration.migrate_button')"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined; oldAsset = undefined"
  >
    <template #header="{ title }">
      <div class="flex flex-row items-center -mt-1 -mb-1 text-black dark:text-white">
        <div class="grow font-medium text-xl">
          {{ title }}
        </div>

        <div class="flex flex-row-reverse">
          <HintMenuIcon>
            <i18n-t
              scope="global"
              keypath="solana_token_migration.hint"
              tag="div"
            >
              <ExternalLink
                :text="t('solana_token_migration.release_notes')"
                :url="externalLinks.usageGuideSection.solanaTokenMigration"
              />
            </i18n-t>
          </HintMenuIcon>
        </div>
      </div>
    </template>
    <SolanaTokenMigrationForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
      :old-asset="oldAsset"
      :loading="loading"
    />
  </BigDialog>
</template>
