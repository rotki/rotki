import { z } from 'zod';
import { api } from '@/modules/core/api/rotki-api';

const CsvImportedEventSummarySchema = z.object({
  customizedEventsCount: z.number(),
  eventsCount: z.number(),
  location: z.string(),
});

export type CsvImportedEventSummary = z.infer<typeof CsvImportedEventSummarySchema>;

interface UseCsvImportedEventsApiReturn {
  deleteCsvImportedEvents: (location?: string) => Promise<boolean>;
  fetchCsvImportedEventsSummary: (location?: string) => Promise<CsvImportedEventSummary[]>;
}

export function useCsvImportedEventsApi(): UseCsvImportedEventsApiReturn {
  const fetchCsvImportedEventsSummary = async (location?: string): Promise<CsvImportedEventSummary[]> => z.array(
    CsvImportedEventSummarySchema,
  ).parse(await api.get<CsvImportedEventSummary[]>('/history/events/imported', {
    query: { location },
    filterEmptyProperties: true,
  }));

  const deleteCsvImportedEvents = async (location?: string): Promise<boolean> => api.delete<boolean>(
    '/history/events/imported',
    {
      body: { location },
      filterEmptyProperties: true,
    },
  );

  return { deleteCsvImportedEvents, fetchCsvImportedEventsSummary };
}
