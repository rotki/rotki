import { api } from '@/modules/api/rotki-api';

export interface CustomizedEventDuplicates {
  autoFixGroupIds: string[];
  manualReviewGroupIds: string[];
}

export interface CustomizedEventDuplicatesFixResult {
  removedEventIdentifiers: number[];
  autoFixGroupIds: string[];
}

interface UseCustomizedEventDuplicatesApiReturn {
  getCustomizedEventDuplicates: () => Promise<CustomizedEventDuplicates>;
  fixCustomizedEventDuplicates: (groupIdentifiers?: string[]) => Promise<CustomizedEventDuplicatesFixResult>;
}

export function useCustomizedEventDuplicatesApi(): UseCustomizedEventDuplicatesApiReturn {
  const getCustomizedEventDuplicates = async (): Promise<CustomizedEventDuplicates> =>
    api.get<CustomizedEventDuplicates>('/history/events/duplicates/customized');

  const fixCustomizedEventDuplicates = async (groupIdentifiers?: string[]): Promise<CustomizedEventDuplicatesFixResult> =>
    api.post<CustomizedEventDuplicatesFixResult>('/history/events/duplicates/customized', {
      ...(groupIdentifiers && { groupIdentifiers }),
    });

  return {
    fixCustomizedEventDuplicates,
    getCustomizedEventDuplicates,
  };
}
