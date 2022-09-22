import { ActionResult } from '@rotki/common/lib/data';
import {
  axiosNoRootCamelCaseTransformer,
  axiosSnakeCaseTransformer
} from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { Tag, Tags } from '@/types/user';

export const useTagsApi = () => {
  const queryTags = async (): Promise<Tags> => {
    const response = await api.instance.get<ActionResult<Tags>>('/tags', {
      validateStatus: validWithSessionStatus
    });

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  };

  const queryAddTag = async (tag: Tag): Promise<Tags> => {
    const response = await api.instance.put<ActionResult<Tags>>(
      '/tags',
      axiosSnakeCaseTransformer(tag),
      {
        validateStatus: validStatus
      }
    );

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  };

  const queryEditTag = async (tag: Tag): Promise<Tags> => {
    const response = await api.instance.patch<ActionResult<Tags>>(
      '/tags',
      axiosSnakeCaseTransformer(tag),
      {
        validateStatus: validStatus
      }
    );

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  };

  const queryDeleteTag = async (tagName: string): Promise<Tags> => {
    const response = await api.instance.delete<ActionResult<Tags>>('/tags', {
      data: {
        name: tagName
      },
      validateStatus: validStatus
    });

    const data = handleResponse(response);
    return Tags.parse(axiosNoRootCamelCaseTransformer(data));
  };

  return {
    queryTags,
    queryAddTag,
    queryEditTag,
    queryDeleteTag
  };
};
