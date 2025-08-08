<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
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

const animateDelete = ref<boolean>(false);
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

function clearDeleteDialog() {
  set(showDeleteConfirmation, false);
  set(idToDelete, null);
  set(animateDelete, false);
}

function confirmDelete() {
  const id = get(idToDelete);
  if (id === null)
    return;

  set(animateDelete, true);
  setTimeout(async () => {
    await deleteUserNote(id);
    clearDeleteDialog();
    await fetchNotes();
  }, 200);
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
    class="note__wrapper flex flex-col gap-3 px-4 pb-4"
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
    class="px-4 pb-4 note__wrapper"
  >
    <CollectionHandler :collection="notes">
      <template #default="{ data, limit }">
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

        <div v-if="data.length > 0">
          <div class="flex flex-col gap-3">
            <template
              v-for="note in data"
              :key="note.identifier"
            >
              <RuiCard
                dense
                class="note__item"
                :class="{
                  'note__item--deleting': animateDelete && idToDelete === note.identifier,
                }"
              >
                <div class="flex justify-between items-center">
                  <div class="font-bold note__title">
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

                <div class="text-rui-text-secondary note__content">
                  {{ note.content }}
                </div>

                <div
                  v-if="showDeleteConfirmation && idToDelete === note.identifier"
                  class="flex justify-between items-center pt-2"
                >
                  <div class="note__content font-italic flex-1">
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
                    class="note__datetime text-rui-text-secondary font-italic flex-1"
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
            </template>
          </div>
        </div>

        <div
          v-else
          class="note__empty text-rui-text"
        >
          {{ t('notes_menu.empty_notes') }}
        </div>
      </template>
    </CollectionHandler>
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
.note {
  &__wrapper {
    max-height: calc(100% - 120px);
    overflow: auto;
  }

  &__title {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    flex: 1;
  }

  &__content {
    white-space: pre-line;
    font-size: 0.85rem;
  }

  &__datetime {
    font-size: 0.85rem;
    opacity: 0;
    transition: 0.2s all;
  }

  &__item {
    transition: 0.2s all;
    overflow: hidden;
    transform-origin: 0 0;

    &:hover {
      .note {
        &__datetime {
          opacity: 1;
        }
      }
    }

    &--deleting {
      transform: scaleY(0);
      opacity: 0;
    }
  }

  &__empty {
    font-size: 1.5rem;
    font-weight: 300;
    margin-top: 2rem;
    text-align: center;
  }
}
</style>
