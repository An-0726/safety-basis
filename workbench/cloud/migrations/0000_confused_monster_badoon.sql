CREATE TABLE `audit` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_id` text NOT NULL,
	`action` text NOT NULL,
	`actor` text NOT NULL,
	`actor_id` text NOT NULL,
	`actor_source` text NOT NULL,
	`detail` text NOT NULL,
	`created_at` text NOT NULL,
	CONSTRAINT "audit_detail_json" CHECK(json_valid("audit"."detail"))
);
--> statement-breakpoint
CREATE INDEX `audit_entity` ON `audit` (`entity_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `findings` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`body` text NOT NULL,
	`position` integer DEFAULT 0 NOT NULL,
	`revision` integer DEFAULT 1 NOT NULL,
	`mutation_id` text DEFAULT '' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "finding_body_json" CHECK(json_valid("findings"."body"))
);
--> statement-breakpoint
CREATE INDEX `finding_project` ON `findings` (`project_id`,`position`);--> statement-breakpoint
CREATE TABLE `photos` (
	`id` text PRIMARY KEY NOT NULL,
	`finding_id` text NOT NULL,
	`filename` text NOT NULL,
	`object_key` text NOT NULL,
	`mime_type` text DEFAULT 'image/jpeg' NOT NULL,
	`width` integer NOT NULL,
	`height` integer NOT NULL,
	`caption` text DEFAULT '' NOT NULL,
	`position` integer DEFAULT 0 NOT NULL,
	`sha256` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`finding_id`) REFERENCES `findings`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `photo_finding` ON `photos` (`finding_id`,`position`);--> statement-breakpoint
CREATE TABLE `projects` (
	`id` text PRIMARY KEY NOT NULL,
	`body` text NOT NULL,
	`revision` integer DEFAULT 1 NOT NULL,
	`mutation_id` text DEFAULT '' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	CONSTRAINT "project_body_json" CHECK(json_valid("projects"."body"))
);
--> statement-breakpoint
CREATE TABLE `reports` (
	`id` text PRIMARY KEY NOT NULL,
	`project_id` text NOT NULL,
	`mode` text NOT NULL,
	`snapshot` text NOT NULL,
	`created_at` text NOT NULL,
	`docx_key` text NOT NULL,
	`pdf_key` text NOT NULL,
	`pdf_engine` text NOT NULL,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "report_snapshot_json" CHECK(json_valid("reports"."snapshot"))
);
--> statement-breakpoint
CREATE INDEX `report_project` ON `reports` (`project_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `reviews` (
	`id` text PRIMARY KEY NOT NULL,
	`finding_id` text NOT NULL,
	`decision` text NOT NULL,
	`reviewer` text NOT NULL,
	`comment` text NOT NULL,
	`revision` integer NOT NULL,
	`actor_id` text NOT NULL,
	`actor_source` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`finding_id`) REFERENCES `findings`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `review_finding` ON `reviews` (`finding_id`,`created_at`);