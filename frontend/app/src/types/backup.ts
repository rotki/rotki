import { z } from 'zod';

const GlobalDbVersion = z.object({
  globaldbAssetsVersion: z.number(),
  globaldbSchemaVersion: z.number()
});
const UserDbInfo = z.object({
  filepath: z.string(),
  size: z.number(),
  version: z.number()
});
const UserDbBackup = z.object({
  size: z.number(),
  time: z.number(),
  version: z.number()
});
export type UserDbBackup = z.infer<typeof UserDbBackup>;
const UserDb = z.object({
  info: UserDbInfo,
  backups: z.array(UserDbBackup)
});
const DatabaseInfo = z.object({
  globaldb: GlobalDbVersion,
  userdb: UserDb
});
export type DatabaseInfo = z.infer<typeof DatabaseInfo>;
export const DatabaseInfoResponse = z.object({
  result: DatabaseInfo,
  message: z.string()
});
export type DatabaseInfoResponse = z.infer<typeof DatabaseInfoResponse>;
export const CreateDatabaseResponse = z.object({
  result: z.string(),
  message: z.string()
});
export type CreateDatabaseResponse = z.infer<typeof CreateDatabaseResponse>;
export const DeleteDatabaseResponse = z.object({
  result: z.boolean(),
  message: z.string()
});
export type DeleteDatabaseResponse = z.infer<typeof DeleteDatabaseResponse>;
