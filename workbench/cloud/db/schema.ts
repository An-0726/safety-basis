import {sql} from 'drizzle-orm';
import {check, index, integer, sqliteTable, text} from 'drizzle-orm/sqlite-core';

// A single owner-private workspace. Visitor identity is audit provenance, not a
// second copy of the owner's records. Sites dispatch owns workspace admission.
export const projects = sqliteTable('projects', {
  id: text('id').primaryKey(),
  body: text('body').notNull(),
  revision: integer('revision').notNull().default(1),
  mutationId: text('mutation_id').notNull().default(''),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
}, table => [check('project_body_json', sql`json_valid(${table.body})`)]);

export const findings = sqliteTable('findings', {
  id: text('id').primaryKey(),
  projectId: text('project_id').notNull().references(() => projects.id),
  body: text('body').notNull(),
  position: integer('position').notNull().default(0),
  revision: integer('revision').notNull().default(1),
  mutationId: text('mutation_id').notNull().default(''),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
}, table => [index('finding_project').on(table.projectId, table.position), check('finding_body_json', sql`json_valid(${table.body})`)]);

export const photos = sqliteTable('photos', {
  id: text('id').primaryKey(),
  findingId: text('finding_id').notNull().references(() => findings.id, {onDelete: 'cascade'}),
  filename: text('filename').notNull(),
  objectKey: text('object_key').notNull(),
  mimeType: text('mime_type').notNull().default('image/jpeg'),
  width: integer('width').notNull(),
  height: integer('height').notNull(),
  caption: text('caption').notNull().default(''),
  position: integer('position').notNull().default(0),
  sha256: text('sha256').notNull(),
  createdAt: text('created_at').notNull(),
}, table => [index('photo_finding').on(table.findingId, table.position)]);

export const reviews = sqliteTable('reviews', {
  id: text('id').primaryKey(),
  findingId: text('finding_id').notNull().references(() => findings.id, {onDelete: 'cascade'}),
  decision: text('decision').notNull(),
  reviewer: text('reviewer').notNull(),
  comment: text('comment').notNull(),
  revision: integer('revision').notNull(),
  actorId: text('actor_id').notNull(),
  actorSource: text('actor_source').notNull(),
  createdAt: text('created_at').notNull(),
}, table => [index('review_finding').on(table.findingId, table.createdAt)]);

export const reports = sqliteTable('reports', {
  id: text('id').primaryKey(),
  projectId: text('project_id').notNull().references(() => projects.id),
  mode: text('mode').notNull(),
  snapshot: text('snapshot').notNull(),
  createdAt: text('created_at').notNull(),
  docxKey: text('docx_key').notNull(),
  pdfKey: text('pdf_key').notNull(),
  pdfEngine: text('pdf_engine').notNull(),
}, table => [index('report_project').on(table.projectId, table.createdAt), check('report_snapshot_json', sql`json_valid(${table.snapshot})`)]);

export const audit = sqliteTable('audit', {
  id: text('id').primaryKey(),
  entityId: text('entity_id').notNull(),
  action: text('action').notNull(),
  actor: text('actor').notNull(),
  actorId: text('actor_id').notNull(),
  actorSource: text('actor_source').notNull(),
  detail: text('detail').notNull(),
  createdAt: text('created_at').notNull(),
}, table => [index('audit_entity').on(table.entityId, table.createdAt), check('audit_detail_json', sql`json_valid(${table.detail})`)]);
