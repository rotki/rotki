import * as logger from 'loglevel';

const ROWLIMIT = 50000;

export default class IndexedDb {
  constructor(
    private dbName: string,
    private dbVersion: number,
    private store: string
  ) {}

  get db(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) {
        reject('Unsupported indexedDB');
      }

      const request = (
        window.indexedDB ||
        (window as any).mozIndexedDB ||
        (window as any).webkitIndexedDB
      ).open(this.dbName, this.dbVersion);

      request.onsuccess = e => {
        resolve((e.target as any).result);
      };
      request.onerror = e => {
        reject(e);
      };
      request.onupgradeneeded = e => {
        const db = (e.target as any).result;
        if (!db.objectStoreNames.contains(this.store)) {
          db.createObjectStore(this.store, {
            keyPath: 'id',
            autoIncrement: true
          });
        }
      };

      request.onblocked = e => {
        reject(e);
      };
    });
  }

  async add(data: any, callback: Function = () => {}) {
    try {
      const db = await this.db;
      const objectStore = db
        .transaction(this.store, 'readwrite')
        .objectStore(this.store);

      const request = objectStore.put(data);

      request.onsuccess = (e: any) => {
        const currentId = e.target.result;

        const cursorRequest = objectStore.openCursor();

        cursorRequest.onsuccess = (e: any) => {
          const cursor = e.target.result;
          if (cursor) {
            const firstId = cursor.value.id;
            const length = currentId - firstId + 1;
            const totalExceeded = length - ROWLIMIT;
            if (totalExceeded > 0) {
              objectStore.delete(
                IDBKeyRange.bound(firstId, firstId + totalExceeded - 1)
              );
            }
          }
        };
      };

      request.onerror = (e: any) => callback(e.target.error);
    } catch (e: any) {
      logger.getLogger('console-only').log(e);
    }
  }

  async getAll(callback: Function) {
    try {
      const db = await this.db;
      const request = db
        .transaction(this.store)
        .objectStore(this.store)
        .openCursor();
      const results: any[] = [];
      request.onsuccess = (e: any) => {
        const cursor = e.target.result;
        if (cursor) {
          cursor.continue();
          results.push(cursor.value);
        } else {
          callback(results);
        }
      };
      request.onerror = (e: any) => callback(e.target.error);
    } catch (e: any) {
      logger.getLogger('console-only').log(e);
    }
  }
}
