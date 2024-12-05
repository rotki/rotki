import { useForm } from '@/composables/form';

export const useCalendarEventForm = createSharedComposable(useForm<boolean>);
