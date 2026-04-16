import type { ActionStatus } from '@/modules/common/action';
import type { Tag, Tags } from '@/modules/tags/tags';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import '@test/i18n';

const mockQueryTags = vi.fn();
const mockQueryAddTag = vi.fn();
const mockQueryEditTag = vi.fn();
const mockQueryDeleteTag = vi.fn();
const mockRemoveTag = vi.fn();
const mockRenameTag = vi.fn();
const mockShowErrorMessage = vi.fn();

vi.mock('@/composables/api/tags', () => ({
  useTagsApi: vi.fn(() => ({
    queryAddTag: mockQueryAddTag,
    queryDeleteTag: mockQueryDeleteTag,
    queryEditTag: mockQueryEditTag,
    queryTags: mockQueryTags,
  })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({
    removeTag: mockRemoveTag,
    renameTag: mockRenameTag,
  })),
}));

vi.mock('@/modules/notifications/use-notifications', () => ({
  getErrorMessage: vi.fn((e: unknown): string => (e instanceof Error ? e.message : String(e))),
  useNotifications: vi.fn(() => ({
    showErrorMessage: mockShowErrorMessage,
  })),
}));

function makeTag(name: string): Tag {
  return {
    backgroundColor: '#000000',
    description: `${name} description`,
    foregroundColor: '#ffffff',
    name,
  };
}

function makeTags(...names: string[]): Tags {
  const tags: Tags = {};
  for (const name of names)
    tags[name] = makeTag(name);
  return tags;
}

describe('useTagOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  async function importModule(): Promise<typeof import('./use-tag-operations')> {
    return import('./use-tag-operations');
  }

  describe('fetchTags', () => {
    it('should populate store with fetched tags', async () => {
      const tags = makeTags('tag1', 'tag2');
      mockQueryTags.mockResolvedValue(tags);

      const { useTagOperations } = await importModule();
      const { fetchTags } = useTagOperations();
      await fetchTags();

      const store = useSessionMetadataStore();
      expect(get(store.allTags)).toEqual(tags);
    });

    it('should not throw on fetch error', async () => {
      mockQueryTags.mockRejectedValue(new Error('Network error'));

      const { useTagOperations } = await importModule();
      const { fetchTags } = useTagOperations();

      await expect(fetchTags()).resolves.toBeUndefined();
    });
  });

  describe('addTag', () => {
    it('should add a tag and update store', async () => {
      const tag = makeTag('newTag');
      const updatedTags = makeTags('newTag');
      mockQueryAddTag.mockResolvedValue(updatedTags);

      const { useTagOperations } = await importModule();
      const { addTag } = useTagOperations();
      const result: ActionStatus = await addTag(tag);

      expect(result.success).toBe(true);
      expect(get(useSessionMetadataStore().allTags)).toEqual(updatedTags);
    });

    it('should show error on failure', async () => {
      mockQueryAddTag.mockRejectedValue(new Error('Add failed'));

      const { useTagOperations } = await importModule();
      const { addTag } = useTagOperations();
      const result: ActionStatus = await addTag(makeTag('fail'));

      expect(result.success).toBe(false);
      expect(result.success === false && result.message).toBe('Add failed');
      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('editTag', () => {
    it('should edit a tag and update store', async () => {
      const tag = makeTag('renamed');
      const updatedTags = makeTags('renamed');
      mockQueryEditTag.mockResolvedValue(updatedTags);

      const { useTagOperations } = await importModule();
      const { editTag } = useTagOperations();
      const result: ActionStatus = await editTag(tag, 'original');

      expect(result.success).toBe(true);
      expect(mockRenameTag).toHaveBeenCalledWith('original', 'renamed');
    });

    it('should not rename when name unchanged', async () => {
      const tag = makeTag('same');
      mockQueryEditTag.mockResolvedValue(makeTags('same'));

      const { useTagOperations } = await importModule();
      const { editTag } = useTagOperations();
      await editTag(tag, 'same');

      expect(mockRenameTag).not.toHaveBeenCalled();
    });

    it('should show error on failure', async () => {
      mockQueryEditTag.mockRejectedValue(new Error('Edit failed'));

      const { useTagOperations } = await importModule();
      const { editTag } = useTagOperations();
      const result: ActionStatus = await editTag(makeTag('x'), 'x');

      expect(result.success).toBe(false);
      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('deleteTag', () => {
    it('should delete a tag and update store', async () => {
      const remaining = makeTags('tag1');
      mockQueryDeleteTag.mockResolvedValue(remaining);

      const { useTagOperations } = await importModule();
      const { deleteTag } = useTagOperations();
      await deleteTag('tag2');

      expect(get(useSessionMetadataStore().allTags)).toEqual(remaining);
      expect(mockRemoveTag).toHaveBeenCalledWith('tag2');
    });

    it('should show error on failure', async () => {
      mockQueryDeleteTag.mockRejectedValue(new Error('Delete failed'));

      const { useTagOperations } = await importModule();
      const { deleteTag } = useTagOperations();
      await deleteTag('x');

      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('attemptTagCreation', () => {
    it('should return true if tag already exists', async () => {
      const tags = makeTags('existing');
      mockQueryTags.mockResolvedValue(tags);

      const { useTagOperations } = await importModule();
      const { attemptTagCreation, fetchTags } = useTagOperations();
      await fetchTags();

      const result = await attemptTagCreation('existing');
      expect(result).toBe(true);
      expect(mockQueryAddTag).not.toHaveBeenCalled();
    });

    it('should create tag with random color if not provided', async () => {
      mockQueryTags.mockResolvedValue({});
      mockQueryAddTag.mockResolvedValue(makeTags('newtag'));

      const { useTagOperations } = await importModule();
      const { attemptTagCreation, fetchTags } = useTagOperations();
      await fetchTags();

      const result = await attemptTagCreation('newtag');
      expect(result).toBe(true);
      expect(mockQueryAddTag).toHaveBeenCalledOnce();
    });

    it('should return false on creation failure', async () => {
      mockQueryTags.mockResolvedValue({});
      mockQueryAddTag.mockRejectedValue(new Error('fail'));

      const { useTagOperations } = await importModule();
      const { attemptTagCreation, fetchTags } = useTagOperations();
      await fetchTags();

      const result = await attemptTagCreation('fail');
      expect(result).toBe(false);
    });
  });
});
