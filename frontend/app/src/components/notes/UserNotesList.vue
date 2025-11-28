<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import UserNotesFormDialog from '@/components/notes/UserNotesFormDialog.vue';
import { useUserNotesApi } from '@/composables/api/session/user-notes';
import { usePremium } from '@/composables/premium';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useSessionAuthStore } from '@/store/session/auth';
import { NoteLocation, type UserNote, type UserNotesRequestPayload } from '@/types/notes';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

const open = defineModel<boolean>('open', { required: true });

const props = withDefaults(defineProps<{ location?: string }>(), {
  location: NoteLocation.GLOBAL,
});

function getDefaultForm() {
  return {
    content: '',
    isPinned: false,
    location: NoteLocation.GLOBAL,
    title: '',
  };
}

const { location } = toRefs(props);
const wrapper = ref<any>(null);

const showDeleteConfirmation = ref<boolean>(false);
const idToDelete = ref<number | null>(null);
const form = ref<Partial<UserNote>>(getDefaultForm());
const editMode = ref<boolean>(false);
const loading = ref<boolean>(false);
const search = ref<string>('');
const titleSubstring = ref<string>('');

const { deleteUserNote, fetchUserNotes, updateUserNote } = useUserNotesApi();

const extraParams = computed(() => ({
  location: get(location),
  titleSubstring: get(titleSubstring),
}));

const {
  fetchData,
  pagination,
  state: notes,
} = usePaginationFilters<UserNote, UserNotesRequestPayload>(fetchUserNotes, {
  defaultSortBy: [{
    column: 'isPinned',
    direction: 'desc',
  }, {
    column: 'lastUpdateTimestamp',
    direction: 'desc',
  }],
  extraParams,
});

const { data, limit } = getCollectionData(notes);

const { t } = useI18n({ useScope: 'global' });

async function fetchNotes(loadingIndicator = false) {
  if (loadingIndicator)
    set(loading, true);

  await fetchData();
  set(loading, false);
}

const { found, limit: itemsPerPage, total } = getCollectionData<UserNote>(notes);

const { showUpgradeRow } = setupEntryLimit(itemsPerPage, found, total);

const page = ref<number>(1);
const nextPageDisabled = ref<boolean>(true);

const LIMIT = 10;
watch(page, (page) => {
  set(pagination, {
    ...get(pagination),
    limit: LIMIT * page,
    page: 1,
  });
});

async function togglePin(note: UserNote) {
  const payload = {
    ...note,
    isPinned: !note.isPinned,
  };

  await callUpdateNote(payload);
}

function resetForm() {
  set(editMode, false);
  set(form, getDefaultForm());
  set(open, false);
}

function addNote() {
  resetForm();
  set(open, true);
}

function editNote(note: UserNote) {
  set(editMode, true);
  set(form, { ...note });
  set(open, true);
}

async function callUpdateNote(payload: Partial<UserNote>) {
  await updateUserNote(payload);
  await fetchNotes();
}

function deleteNote(identifier: number) {
  set(showDeleteConfirmation, true);
  set(idToDelete, identifier);
}

function clearDeleteDialog(): void {
  set(showDeleteConfirmation, false);
  set(idToDelete, null);
}

async function confirmDelete(): Promise<void> {
  const id = get(idToDelete);
  if (id === null)
    return;

  await deleteUserNote(id);
  clearDeleteDialog();
  await fetchNotes();
}

function onBeforeLeave(el: Element): void {
  const element = el as HTMLElement;
  element.style.height = `${element.offsetHeight}px`;
  element.style.width = `${element.offsetWidth}px`;
}

const premium = usePremium();
const { logged } = storeToRefs(useSessionAuthStore());

watch([premium], async () => {
  if (get(logged))
    await fetchNotes();
});

debouncedWatch(
  search,
  (search) => {
    set(titleSubstring, search);
  },
  { debounce: 400 },
);

onMounted(async () => {
  await fetchNotes(true);
});

const { arrivedState } = useScroll(wrapper);

watch(notes, (notes) => {
  set(nextPageDisabled, notes.data.length >= notes.found);
});

const bottom = ref<boolean>(false);
watch(arrivedState, (arrived) => {
  set(bottom, arrived.bottom && get(notes).data.length > 0);
});

const shouldIncreasePage = logicAnd(bottom, logicNot(nextPageDisabled));
watch(shouldIncreasePage, (increasePage) => {
  if (increasePage)
    set(page, get(page) + 1);
});
</script>

<template>
  <div class="p-4 flex items-center gap-3">
    <RuiTextField
      v-model="search"
      variant="outlined"
      color="primary"
      dense
      class="flex-1"
      prepend-icon="lu-search"
      :label="t('notes_menu.search')"
      clearable
      hide-details
    />

    <RuiButton
      color="primary"
      class="py-2"
      :disabled="showUpgradeRow"
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
      class="[&>div]:flex [&>div]:flex-col"
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
        >
          <div class="flex justify-between items-center">
            <div class="font-bold overflow-hidden whitespace-nowrap text-ellipsis flex-1">
              {{ note.title }}
            </div>
            <RuiButton
              class="!p-2"
              variant="text"
              icon
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
    v-model="form"
    :edit-mode="editMode"
    :location="location"
    @reset="resetForm()"
    @refresh="fetchNotes()"
  />
</template>

<style lang="scss" scoped>
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
