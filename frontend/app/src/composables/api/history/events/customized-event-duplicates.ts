import { api } from '@/modules/api/rotki-api';

export interface CustomizedEventDuplicates {
  autoFixGroupIds: string[];
  ignoredGroupIds: string[];
  manualReviewGroupIds: string[];
}

export interface CustomizedEventDuplicatesFixResult {
  removedEventIdentifiers: number[];
  autoFixGroupIds: string[];
}

interface UseCustomizedEventDuplicatesApiReturn {
  fixCustomizedEventDuplicates: (groupIdentifiers?: string[]) => Promise<CustomizedEventDuplicatesFixResult>;
  getCustomizedEventDuplicates: () => Promise<CustomizedEventDuplicates>;
  ignoreCustomizedEventDuplicates: (groupIdentifiers: string[]) => Promise<string[]>;
  unignoreCustomizedEventDuplicates: (groupIdentifiers: string[]) => Promise<string[]>;
}

export function useCustomizedEventDuplicatesApi(): UseCustomizedEventDuplicatesApiReturn {
  const getCustomizedEventDuplicates = async (): Promise<CustomizedEventDuplicates> =>
    api.get<CustomizedEventDuplicates>('/history/events/duplicates/customized');

  const fixCustomizedEventDuplicates = async (groupIdentifiers?: string[]): Promise<CustomizedEventDuplicatesFixResult> =>
    api.post<CustomizedEventDuplicatesFixResult>('/history/events/duplicates/customized', {
      ...(groupIdentifiers && { groupIdentifiers }),
    });

  const ignoreCustomizedEventDuplicates = async (groupIdentifiers: string[]): Promise<string[]> =>
    api.put<string[]>('/history/events/duplicates/customized', { groupIdentifiers });

  const unignoreCustomizedEventDuplicates = async (groupIdentifiers: string[]): Promise<string[]> =>
    api.delete<string[]>('/history/events/duplicates/customized', {
      body: { groupIdentifiers },
    });

  return {
    fixCustomizedEventDuplicates,
    getCustomizedEventDuplicates,
    ignoreCustomizedEventDuplicates,
    unignoreCustomizedEventDuplicates,
  };
}
