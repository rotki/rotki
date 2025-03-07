import { type ConsolaInstance, createConsola, LogLevels } from 'consola';

const ROWLIMIT = 50000;

export class IndexedDb {
  private logger: ConsolaInstance;

  constructor(
    private dbName: string,
    private dbVersion: number,
    private store: string,
  ) {
    this.logger = createConsola({
      level: LogLevels.error,
    });
  }

  get db(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB)
        reject(new Error('Unsupported indexedDB'));

      const request = (window.indexedDB || (window as any).mozIndexedDB || (window as any).webkitIndexedDB).open(
        this.dbName,
        this.dbVersion,
      );

      request.onsuccess = (e): void => {
        resolve((e.target as any).result);
      };
      request.onerror = (e): void => {
        reject(e);
      };
      request.onupgradeneeded = (e): void => {
        const db = (e.target as any).result;
        if (!db.objectStoreNames.contains(this.store)) {
          db.createObjectStore(this.store, {
            autoIncrement: true,
            keyPath: 'id',
          });
        }
      };

      request.onblocked = (e): void => {
        reject(e);
      };
    });
  }

  async add(data: any, callback?: (e: any) => void): Promise<void> {
    try {
      const db = await this.db;
      const objectStore = db.transaction(this.store, 'readwrite').objectStore(this.store);

      const request = objectStore.put(data);

      request.onsuccess = (e: any): void => {
        const currentId = e.target.result;

        const cursorRequest = objectStore.openCursor();

        cursorRequest.onsuccess = (e: any): void => {
          const cursor = e.target.result;
          if (cursor) {
            const firstId = cursor.value.id;
            const length = currentId - firstId + 1;
            const totalExceeded = length - ROWLIMIT;
            if (totalExceeded > 0)
              objectStore.delete(IDBKeyRange.bound(firstId, firstId + totalExceeded - 1));
          }
        };
      };

      request.onerror = (e: any): void => callback?.(e.target.error);
    }
    catch (error: any) {
      this.logger.error(error);
    }
  }

  async getAll(callback: (result: any[]) => void): Promise<void> {
    try {
      const db = await this.db;
      const request = db.transaction(this.store).objectStore(this.store).openCursor();
      const results: any[] = [];
      request.onsuccess = (e: any): void => {
        const cursor = e.target.result;
        if (cursor) {
          cursor.continue();
          results.push(cursor.value);
        }
        else {
          callback(results);
        }
      };
      request.onerror = (e: any): void => callback(e.target.error);
    }
    catch (error: any) {
      this.logger.error(error);
    }
  }
}
