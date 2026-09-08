<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import { useUserNotesList } from '@/modules/notes/use-user-notes-list';
import UserNotesFormDialog from '@/modules/notes/UserNotesFormDialog.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const open = defineModel<boolean>('open', { required: true });

const { location = NoteLocation.GLOBAL } = defineProps<{ location?: string }>();

const { t } = useI18n({ useScope: 'global' });

const wrapper = useTemplateRef<HTMLDivElement>('wrapper');
const { arrivedState } = useScroll(wrapper);

const {
  addNote,
  clearDeleteDialog,
  confirmDelete,
  data,
  deleteNote,
  editMode,
  editNote,
  idToDelete,
  limit,
  loadInitialNotes,
  loading,
  modelForm,
  modelSearch,
  onBeforeLeave,
  refreshNotes,
  resetForm,
  showDeleteConfirmation,
  showUpgradeRow,
  togglePin,
} = useUserNotesList({
  arrivedBottom: () => arrivedState.bottom,
  location: () => location,
  open,
});

onMounted(async () => {
  await loadInitialNotes();
});
</script>

<template>
  <div class="p-4 flex items-center gap-3">
    <RuiTextField
      v-model="modelSearch"
      variant="outlined"
      color="primary"
      dense
      class="flex-1"
      prepend-icon="lu-search"
      :label="t('notes_menu.search')"
      clearable
      hide-details
      data-testid="notes-search"
    />

    <RuiButton
      color="primary"
      class="py-2"
      :disabled="showUpgradeRow"
      data-testid="notes-add"
      @click="addNote()"
    >
      <template #prepend>
        <RuiIcon name="lu-plus" />
      </template>
    </RuiButton>
  </div>

  <div
    v-if="loading"
    class="max-h-[calc(100%-120px)] overflow-auto flex-1 flex flex-col gap-3 px-4 pb-4"
  >
    <RuiCard
      v-for="n in 10"
      :key="n"
      :class-names="{ content: 'flex flex-col' }"
    >
      <RuiSkeletonLoader class="w-20 mb-3" />
      <RuiSkeletonLoader class="w-24 mb-6" />
      <RuiSkeletonLoader class="w-16 self-end" />
    </RuiCard>
  </div>

  <div
    v-else
    ref="wrapper"
    class="px-4 pb-4 max-h-[calc(100%-120px)] overflow-auto flex-1"
  >
    <RuiAlert
      v-if="showUpgradeRow"
      type="warning"
      class="mb-4"
    >
      <i18n-t
        scope="global"
        keypath="notes_menu.limit_warning"
        tag="span"
      >
        <template #limit>
          {{ limit }}
        </template>
        <template #link>
          <ExternalLink
            :text="t('upgrade_row.rotki_premium')"
            color="warning"
            premium
          />
        </template>
      </i18n-t>
    </RuiAlert>

    <div
      v-if="data.length > 0"
      class="relative"
    >
      <TransitionGroup
        name="note-list"
        tag="div"
        class="flex flex-col gap-3"
        @before-leave="onBeforeLeave($event)"
      >
        <RuiCard
          v-for="note in data"
          :key="note.identifier"
          dense
          class="overflow-hidden group"
          data-testid="note-card"
        >
          <div class="flex justify-between items-center">
            <div class="font-bold overflow-hidden whitespace-nowrap text-ellipsis flex-1">
              {{ note.title }}
            </div>
            <RuiButton
              class="!p-2"
              variant="text"
              icon
              data-testid="note-pin"
              @click="togglePin(note)"
            >
              <RuiIcon
                v-if="note.isPinned"
                color="primary"
                size="20"
                name="lu-pin"
                class="[&_path]:fill-rui-primary"
              />
              <RuiIcon
                v-else
                size="20"
                name="lu-pin"
              />
            </RuiButton>
          </div>

          <div class="text-rui-text-secondary whitespace-pre-line text-sm">
            {{ note.content }}
          </div>

          <div
            v-if="showDeleteConfirmation && idToDelete === note.identifier"
            class="flex justify-between items-center pt-2"
          >
            <div class="whitespace-pre-line text-sm font-italic flex-1">
              {{ t('notes_menu.delete_confirmation') }}
            </div>
            <RuiButton
              variant="text"
              icon
              size="sm"
              color="error"
              data-testid="note-delete-cancel"
              @click="clearDeleteDialog()"
            >
              <RuiIcon
                size="16"
                color="error"
                name="lu-x"
              />
            </RuiButton>

            <RuiButton
              variant="text"
              icon
              size="sm"
              data-testid="note-delete-confirm"
              @click="confirmDelete()"
            >
              <RuiIcon
                size="16"
                color="success"
                name="lu-check"
              />
            </RuiButton>
          </div>
          <div
            v-else
            class="flex justify-between items-center pt-2"
          >
            <i18n-t
              scope="global"
              keypath="notes_menu.last_updated"
              class="text-sm opacity-0 transition-all duration-200 group-hover:opacity-100 text-rui-text-secondary font-italic flex-1"
              tag="span"
            >
              <template #datetime>
                <DateDisplay :timestamp="note.lastUpdateTimestamp" />
              </template>
            </i18n-t>
            <RuiButton
              variant="text"
              icon
              size="sm"
              data-testid="note-edit"
              @click="editNote(note)"
            >
              <RuiIcon
                size="16"
                name="lu-pencil"
              />
            </RuiButton>
            <RuiButton
              variant="text"
              icon
              size="sm"
              data-testid="note-delete"
              @click="deleteNote(note.identifier)"
            >
              <RuiIcon
                size="16"
                name="lu-trash-2"
              />
            </RuiButton>
          </div>
        </RuiCard>
      </TransitionGroup>
    </div>

    <div
      v-else
      class="text-2xl font-light mt-8 text-center text-rui-text"
    >
      {{ t('notes_menu.empty_notes') }}
    </div>
  </div>

  <UserNotesFormDialog
    v-model:open="open"
    v-model="modelForm"
    :edit-mode="editMode"
    :location="location"
    @reset="resetForm()"
    @refresh="refreshNotes()"
  />
</template>

<style scoped>
.note-list-move,
.note-list-enter-active,
.note-list-leave-active {
  @apply transition-all duration-300 ease-in-out;
}

.note-list-enter-from,
.note-list-leave-to {
  @apply opacity-0 scale-[0.85];
}

.note-list-leave-active {
  @apply absolute -z-10;
}
</style>
