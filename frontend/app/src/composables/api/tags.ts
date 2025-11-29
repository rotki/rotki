import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { type Tag, Tags } from '@/types/tags';

interface UseTagsApiReturn {
  queryTags: () => Promise<Tags>;
  queryAddTag: (tag: Tag) => Promise<Tags>;
  queryEditTag: (tag: Tag) => Promise<Tags>;
  queryDeleteTag: (tagName: string) => Promise<Tags>;
}

export function useTagsApi(): UseTagsApiReturn {
  const queryTags = async (): Promise<Tags> => {
    const data = await api.get<Tags>('/tags', {
      validStatuses: VALID_WITH_SESSION_STATUS,
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  const queryAddTag = async (tag: Tag): Promise<Tags> => {
    const data = await api.put<Tags>('/tags', tag, {
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  const queryEditTag = async (tag: Tag): Promise<Tags> => {
    const data = await api.patch<Tags>('/tags', tag, {
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  const queryDeleteTag = async (tagName: string): Promise<Tags> => {
    const data = await api.delete<Tags>('/tags', {
      body: {
        name: tagName,
      },
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  return {
    queryAddTag,
    queryDeleteTag,
    queryEditTag,
    queryTags,
  };
}
