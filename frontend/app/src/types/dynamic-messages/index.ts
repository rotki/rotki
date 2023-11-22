import { z } from 'zod';

const Action = z.object({
  text: z.string(),
  url: z.string()
});

const VisiblityPeriod = z.object({
  start: z.number().positive(),
  end: z.number().positive()
});

export type VisibilityPeriod = z.infer<typeof VisiblityPeriod>;

const WelcomeMessage = z.object({
  header: z.string().optional(),
  icon: z.string().optional(),
  text: z.string(),
  action: Action.optional(),
  period: VisiblityPeriod
});

export type WelcomeMessage = z.infer<typeof WelcomeMessage>;

export const WelcomeSchema = z.object({
  header: z.string().optional(),
  text: z.string().optional(),
  messages: z.array(WelcomeMessage)
});

export type WelcomeSchema = z.infer<typeof WelcomeSchema>;

const DashboardMessage = z.object({
  message: z.string(),
  messageHighlight: z.string().optional(),
  action: Action.optional(),
  period: VisiblityPeriod
});

export type DashboardMessage = z.infer<typeof DashboardMessage>;

export const DashboardSchema = z.array(DashboardMessage);

export type DashboardSchema = z.infer<typeof DashboardSchema>;
