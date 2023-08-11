<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { type Collection } from '@/types/collection';
import { type UserNote, type UserNotesFilter } from '@/types/notes';
import UserNotesFormDialog from '@/components/notes/UserNotesFormDialog.vue';

const props = defineProps({
  location: {
    required: false,
    type: String,
    default: ''
  }
});

const getDefaultForm = () => ({
  title: '',
  content: '',
  isPinned: false,
  location: ''
});

const { location } = toRefs(props);
const wrapper = ref<any>(null);

const notes = ref<Collection<UserNote>>(defaultCollectionState<UserNote>());

const animateDelete = ref<boolean>(false);
const showDeleteConfirmation = ref<boolean>(false);
const idToDelete = ref<number | null>(null);
const form = ref<Partial<UserNote>>(getDefaultForm());
const editMode = ref<boolean>(false);
const loading = ref<boolean>(false);
const search = ref<string>('');
const itemsPerPage = 10;

const filter = ref<UserNotesFilter>({
  limit: itemsPerPage,
  offset: 0,
  titleSubstring: '',
  location: get(location),
  orderByAttributes: ['is_pinned', 'last_update_timestamp'],
  ascending: [false, false]
});

const { t } = useI18n();
const { premiumURL } = useInterop();

const api = useUserNotesApi();

const fetchNotes = async (loadingIndicator = false) => {
  if (loadingIndicator) {
    set(loading, true);
  }
  set(notes, await api.fetchUserNotes(get(filter)));
  if (loadingIndicator) {
    set(loading, false);
  }
  nextTick(() => {
    if (get(wrapper)) {
      get(wrapper).scrollTop = 0;
    }
  });
};

const page = computed<number>(() => {
  const offset = get(filter).offset;

  return offset / itemsPerPage + 1;
});

const { limit, found, total } = getCollectionData<UserNote>(notes);

const { showUpgradeRow } = setupEntryLimit(limit, found, total);

const totalPage = computed<number>(() => {
  const foundVal = get(found);
  const limitVal = get(limit);
  const shown = limitVal !== -1 ? limitVal : foundVal;

  return Math.ceil(shown / itemsPerPage);
});

watch([page, totalPage], ([page, totalPage]) => {
  if (page > 1 && page > totalPage) {
    changePage(page - 1);
  }
});

const togglePin = async (note: UserNote) => {
  const payload = {
    ...note,
    isPinned: !note.isPinned
  };

  await callUpdateNote(payload);
};

const resetForm = () => {
  set(editMode, false);
  set(form, getDefaultForm());
  closeDialog();
};

const { closeDialog, setOpenDialog, setSubmitFunc } = useUserNotesForm();

const addNote = () => {
  resetForm();
  setOpenDialog(true);
};

const editNote = (note: UserNote) => {
  set(editMode, true);
  set(form, { ...note });
  setOpenDialog(true);
};

const callUpdateNote = async (payload: Partial<UserNote>) => {
  await api.updateUserNote(payload);
  await fetchNotes();
};

const save = async () => {
  try {
    if (get(editMode)) {
      await callUpdateNote(get(form));
    } else {
      await api.addUserNote({ ...get(form), location: get(location) });
      await fetchNotes();
    }
    resetForm();
  } catch (e) {
    logger.error(e);
  }
};
setSubmitFunc(save);

const deleteNote = async (identifier: number) => {
  set(showDeleteConfirmation, true);
  set(idToDelete, identifier);
};

const clearDeleteDialog = () => {
  set(showDeleteConfirmation, false);
  set(idToDelete, null);
  set(animateDelete, false);
};

const confirmDelete = async () => {
  const id = get(idToDelete);
  if (id === null) {
    return;
  }
  set(animateDelete, true);
  setTimeout(async () => {
    await api.deleteUserNote(id);
    clearDeleteDialog();
    await fetchNotes();
  }, 200);
};

const premium = usePremium();
const { logged } = storeToRefs(useSessionAuthStore());

watch([filter, premium], async () => {
  if (get(logged)) {
    await fetchNotes();
  }
});

debouncedWatch(
  search,
  () => {
    set(filter, {
      ...get(filter),
      titleSubstring: get(search),
      offset: 0
    });
  },
  { debounce: 400 }
);

const changePage = (page: number) => {
  set(filter, {
    ...get(filter),
    offset: (page - 1) * itemsPerPage
  });
};

onMounted(async () => {
  await fetchNotes(true);
});
</script>

<template>
  <Fragment>
    <div class="pa-4 pb-0">
      <div class="mb-4 d-flex items-center">
        <VBtn
          rounded
          color="primary"
          fab
          small
          depressed
          :disabled="showUpgradeRow"
          @click="addNote()"
        >
          <VIcon>mdi-plus</VIcon>
        </VBtn>

        <VTextField
          v-model="search"
          outlined
          dense
          class="ml-4"
          prepend-inner-icon="mdi-magnify"
          :label="t('notes_menu.search')"
          clearable
          hide-details
        />
      </div>
    </div>

    <div v-if="loading" class="d-flex justify-center pt-2">
      <VProgressCircular color="primary" indeterminate width="2" size="50" />
    </div>

    <div v-else ref="wrapper" class="px-4 note__wrapper">
      <VAlert
        v-if="showUpgradeRow"
        type="warning"
        text
        class="pa-2 text-subtitle-2"
      >
        <i18n path="notes_menu.limit_warning">
          <template #limit>{{ itemsPerPage }}</template>
          <template #link>
            <BaseExternalLink
              :text="t('upgrade_row.rotki_premium')"
              :href="premiumURL"
            />
          </template>
        </i18n>
      </VAlert>

      <div v-if="notes.data.length > 0">
        <div>
          <template v-for="note in notes.data">
            <VSheet
              :key="note.identifier"
              outlined
              rounded
              class="note__item pa-3 pt-2 mb-4"
              :class="{
                'note__item--deleting':
                  animateDelete && idToDelete === note.identifier
              }"
            >
              <div class="d-flex justify-space-between align-center">
                <div class="font-weight-bold note__title">
                  {{ note.title }}
                </div>
                <VBtn icon @click="togglePin(note)">
                  <VIcon v-if="note.isPinned" color="primary">mdi-pin</VIcon>
                  <VIcon v-else color="gray">mdi-pin-outline</VIcon>
                </VBtn>
              </div>

              <div class="text--secondary note__content">
                {{ note.content }}
              </div>

              <div
                v-if="showDeleteConfirmation && idToDelete === note.identifier"
                class="d-flex justify-space-between align-center pt-2"
              >
                <div class="note__content font-italic">
                  {{ t('notes_menu.delete_confirmation') }}
                </div>
                <div>
                  <VBtn icon small @click="clearDeleteDialog()">
                    <VIcon small color="red">mdi-close</VIcon>
                  </VBtn>

                  <VBtn icon small @click="confirmDelete()">
                    <VIcon small color="green">mdi-check</VIcon>
                  </VBtn>
                </div>
              </div>
              <div
                v-else
                class="d-flex justify-space-between align-center pt-2"
              >
                <div class="note__datetime text--secondary font-italic">
                  <i18n path="notes_menu.last_updated">
                    <template #datetime>
                      <DateDisplay :timestamp="note.lastUpdateTimestamp" />
                    </template>
                  </i18n>
                </div>
                <div>
                  <VBtn icon small @click="editNote(note)">
                    <VIcon small>mdi-pencil-outline</VIcon>
                  </VBtn>

                  <VBtn icon small @click="deleteNote(note.identifier)">
                    <VIcon small>mdi-delete-outline</VIcon>
                  </VBtn>
                </div>
              </div>
            </VSheet>
          </template>

          <div v-if="totalPage > 1" class="mb-4">
            <VPagination
              :value="page"
              :length="totalPage"
              @input="changePage($event)"
            />
          </div>
        </div>
      </div>

      <div v-else class="note__empty text-rui-text">
        {{ t('notes_menu.empty_notes') }}
      </div>
    </div>

    <UserNotesFormDialog
      v-model="form"
      :edit-mode="editMode"
      @reset="resetForm()"
    />
  </Fragment>
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
