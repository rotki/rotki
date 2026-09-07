<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { useTemplateRef } from 'vue';
import { type SolanaTokenMigrationData, useSolanaTokenMigrationDialog } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-dialog';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import SolanaTokenMigrationForm from './SolanaTokenMigrationForm.vue';

const modelValue = defineModel<SolanaTokenMigrationData | undefined>({ required: true });
const oldAsset = defineModel<string | undefined>('oldAsset', { required: false });

const emit = defineEmits<{
  'refresh': [];
  'suggest-merge': [event: { sourceAsset: string; targetAsset: string }];
}>();

const { t } = useI18n({ useScope: 'global' });

const form = useTemplateRef<InstanceType<typeof SolanaTokenMigrationForm>>('form');
const stateUpdated = ref<boolean>(false);

const { loading, modelErrorMessages, save } = useSolanaTokenMigrationDialog({
  modelValue,
  oldAsset,
  onMigrated: (): void => emit('refresh'),
  onSuggestMerge: (suggestion): void => emit('suggest-merge', suggestion),
  validateForm: (): boolean => get(form)?.validate() ?? false,
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="t('asset_management.solana_token_migration.dialog_title')"
    :action="{ primary: t('asset_management.solana_token_migration.migrate_button') }"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined; oldAsset = undefined"
  >
    <template #header="{ title }">
      <div class="flex items-center -mt-1 -mb-1 text-black dark:text-white">
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
      v-model:error-messages="modelErrorMessages"
      v-model:state-updated="stateUpdated"
      :old-asset="oldAsset"
      :loading="loading"
    />
  </BigDialog>
</template>
