import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface CalendarEventMessages {
  name: string;
}

/**
 * The name is the only rule the form has ever had. Everything else is carried, and most of it has
 * no field bound to show a message, so a structural rule here would block the save with nothing on
 * screen to explain it. Server-side failures arrive through `setServerErrors` instead.
 */
export function calendarEventSchema(messages: CalendarEventMessages): ZodType {
  return z.object({
    name: requiredField(messages.name),
  }).passthrough();
}
