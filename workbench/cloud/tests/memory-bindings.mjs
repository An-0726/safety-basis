/** In-memory Cloudflare bindings for isolated local integration tests.
 * D1 executes real SQLite SQL and atomic batch transactions; R2 bytes never leave
 * this process. These are test adapters, not production persistence.
 */
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';

class D1Statement {
  constructor(database, sql, values = []) { this.database = database; this.sql = sql; this.values = values; }
  bind(...values) { return new D1Statement(this.database, this.sql, values); }
  execute() {
    const db = this.database.connection;
    const beforeChanges = db.prepare('SELECT total_changes() AS value').get().value;
    const results = db.prepare(this.sql).all(...this.values).map(row => ({...row}));
    const afterChanges = db.prepare('SELECT total_changes() AS value').get().value;
    return {success: true, results, meta: {
      changes: Number(afterChanges - beforeChanges),
      last_row_id: Number(db.prepare('SELECT last_insert_rowid() AS value').get().value),
      rows_read: results.length, rows_written: Number(afterChanges - beforeChanges), duration: 0,
    }};
  }
  async all() { return this.execute(); }
  async run() { return this.execute(); }
  async first(column) {
    const row = this.execute().results[0] || null;
    if (column !== undefined && row && !(column in row)) throw new Error(`D1 column not found: ${column}`);
    return column === undefined ? row : row?.[column] ?? null;
  }
  async raw({columnNames = false} = {}) {
    const rows = this.execute().results;
    return columnNames && rows.length ? [Object.keys(rows[0]), ...rows.map(Object.values)] : rows.map(Object.values);
  }
}

export class MemoryD1 {
  constructor() {
    this.connection = new DatabaseSync(':memory:');
    this.connection.exec('PRAGMA foreign_keys=ON;');
  }
  prepare(sql) { return new D1Statement(this, sql); }
  async exec(sql) { this.connection.exec(sql); return {count: 1, duration: 0}; }
  async batch(statements) {
    this.connection.exec('BEGIN IMMEDIATE');
    try {
      const results = statements.map(statement => {
        assert.equal(statement.database, this, 'D1 batch cannot cross databases');
        return statement.execute();
      });
      this.connection.exec('COMMIT');
      return results;
    } catch (error) {
      this.connection.exec('ROLLBACK');
      throw error;
    }
  }
  withSession() { return this; }
  close() { this.connection.close(); }
}

export class MemoryR2 {
  constructor() { this.objects = new Map(); }
  metadata(key, value) {
    return {key, version: value.etag, size: value.bytes.byteLength, etag: value.etag,
      httpEtag: `"${value.etag}"`, uploaded: value.uploaded,
      httpMetadata: {...value.httpMetadata}, customMetadata: {...value.customMetadata},
      writeHttpMetadata(headers) {
        for (const [field, header] of Object.entries({contentType: 'Content-Type', contentDisposition: 'Content-Disposition', cacheControl: 'Cache-Control'})) {
          if (value.httpMetadata[field]) headers.set(header, value.httpMetadata[field]);
        }
      },
    };
  }
  async put(key, input, options = {}) {
    const bytes = new Uint8Array(await new Response(input).arrayBuffer());
    const etag = createHash('sha256').update(bytes).digest('hex');
    const value = {bytes, etag, uploaded: new Date(), httpMetadata: {...options.httpMetadata}, customMetadata: {...options.customMetadata}};
    this.objects.set(key, value);
    return this.metadata(key, value);
  }
  async get(key) {
    const value = this.objects.get(key);
    if (!value) return null;
    const bytes = new Uint8Array(value.bytes);
    return {...this.metadata(key, value), body: new Response(bytes).body, bodyUsed: false,
      arrayBuffer: async () => bytes.slice().buffer,
      text: async () => new TextDecoder().decode(bytes),
      json: async () => JSON.parse(new TextDecoder().decode(bytes)),
      blob: async () => new Blob([bytes], {type: value.httpMetadata.contentType || ''}),
    };
  }
  async head(key) { const value = this.objects.get(key); return value ? this.metadata(key, value) : null; }
  async delete(keys) { for (const key of Array.isArray(keys) ? keys : [keys]) this.objects.delete(key); }
  async list({prefix = '', limit = 1000, cursor} = {}) {
    const matches = [...this.objects.entries()].filter(([key]) => key.startsWith(prefix)).sort(([a], [b]) => a.localeCompare(b));
    const offset = Number(cursor || 0);
    const entries = matches.slice(offset, offset + limit);
    const truncated = offset + entries.length < matches.length;
    return {objects: entries.map(([key, value]) => this.metadata(key, value)), truncated,
      cursor: truncated ? String(offset + entries.length) : undefined, delimitedPrefixes: []};
  }
}
