<script setup lang="ts">
import { NotificationKind, Severity } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { useAddressBookImport } from '@/modules/accounts/address-book/use-address-book-import';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const emit = defineEmits<{
  refresh: [];
}>();

const importFile = ref<File>();
const importDialogOpen = ref<boolean>(false);
const loading = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
const { importAddressBook } = useAddressBookImport();
const { notify } = useNotificationDispatcher();

async function doImport() {
  if (!isDefined(importFile)) {
    return;
  }
  const file = get(importFile);
  set(loading, true);
  set(importDialogOpen, false);
  const successEntries = await importAddressBook(file);
  set(importFile, undefined);
  set(loading, false);
  if (successEntries > 0) {
    notify({
      message: t('address_book.import.import_success.message', {
        length: successEntries,
      }),
      kind: NotificationKind.RESULT,
      severity: Severity.INFO,
      title: t('address_book.import.title'),
    });
  }
  emit('refresh');
}
</script>

<template>
  <div>
    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          data-testid="address-book-import"
          @click="importDialogOpen = true"
        >
          <template #prepend>
            <RuiIcon name="lu-file-up" />
          </template>
          {{ t('common.actions.import') }}
        </RuiButton>
      </template>
      {{ t('address_book.import.title') }}
    </RuiTooltip>
    <RuiDialog
      v-model="importDialogOpen"
      max-width="560"
    >
      <RuiCard>
        <template #header>
          {{ t('address_book.import.title') }}
        </template>
        <template #subheader>
          {{ t('address_book.import.description') }}
        </template>
        <RuiFileUpload
          v-model="importFile"
          accept=".csv"
          :disabled="loading"
          :upload-text="t('file_upload.dropzone.prefix')"
          :click-to-upload-text="t('file_upload.dropzone.choose')"
          :replace-text="t('file_upload.dropzone.replace')"
          data-testid="address-book-import-file"
        />
        <div class="mt-2 text-sm text-rui-text-secondary">
          <i18n-t
            scope="global"
            keypath="blockchain_balances.import_csv_example"
          >
            <template #here>
              <ExternalLink
                color="primary"
                :url="externalLinks.usageGuideSection.importAddressBook"
              >
                {{ t('common.here') }}
              </ExternalLink>
            </template>
          </i18n-t>
        </div>
        <template #footer>
          <div class="grow" />
          <RuiButton
            variant="outlined"
            color="primary"
            data-testid="address-book-import-cancel"
            @click="importDialogOpen = false"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="!importFile"
            :loading="loading"
            data-testid="address-book-import-confirm"
            @click="doImport()"
          >
            {{ t('common.actions.import') }}
          </RuiButton>
        </template>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
