<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import { useAddressBookImport } from '@/composables/address-book/use-address-book-import';
import { useNotificationsStore } from '@/store/notifications';
import { Severity } from '@rotki/common';
import { externalLinks } from '@shared/external-links';

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const importFileUploader = useTemplateRef<ComponentExposed<typeof FileUpload>>('uploader');
const importFile = ref<File>();
const importDialogOpen = ref<boolean>(false);
const loading = ref<boolean>(false);

const { t } = useI18n();
const { importAddressBook } = useAddressBookImport();
const { notify } = useNotificationsStore();

async function doImport() {
  if (!isDefined(importFile)) {
    return;
  }
  const file = get(importFile);
  set(loading, true);
  set(importDialogOpen, false);
  const successEntries = await importAddressBook(file);
  set(importFile, undefined);
  get(importFileUploader)?.removeFile();
  set(loading, false);
  if (successEntries > 0) {
    notify({
      display: true,
      message: t('address_book.import.import_success.message', {
        length: successEntries,
      }),
      severity: Severity.INFO,
      title: t('address_book.import.title'),
    });
  }
  emit('refresh');
}
</script>

<template>
  <div>
    <RuiMenu
      :popper="{ placement: 'bottom-end' }"
      menu-class="max-w-[24rem]"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="!p-2"
          v-bind="attrs"
        >
          <RuiIcon name="lu-ellipsis-vertical" />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton
          variant="list"
          @click="importDialogOpen = true;"
        >
          <template #prepend>
            <RuiIcon name="lu-file-up" />
          </template>
          {{ t('address_book.import.title') }}
        </RuiButton>
      </div>
    </RuiMenu>
    <RuiDialog
      v-model="importDialogOpen"
      max-width="600"
    >
      <RuiCard>
        <template #header>
          {{ t('address_book.import.title') }}
        </template>
        <FileUpload
          ref="uploader"
          v-model="importFile"
          source="csv"
          file-filter=".csv"
        />
        <div class="mt-2 text-caption text-rui-text-secondary">
          <i18n-t keypath="blockchain_balances.import_csv_example">
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
            variant="text"
            color="primary"
            @click="importDialogOpen = false"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="!importFile"
            :loading="loading"
            @click="doImport()"
          >
            {{ t('common.actions.import') }}
          </RuiButton>
        </template>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
