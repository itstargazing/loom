/**
 * Mirrors the backend response models in `backend/app/schemas/`.
 *
 * Kept hand-written rather than generated so the dashboard can be read without
 * a build step; `npm run check:api` compares these against the live OpenAPI
 * schema and fails if the two drift apart.
 */

export interface SkillCount {
  skill: string;
  label: string;
  count: number;
}

export interface ActivityItem {
  skill: string;
  label: string;
  title: string;
  detail: string | null;
  sourceUrl: string;
  pageTitle: string;
  confidence: number;
  timesSeen: number;
  lastSeenAt: string;
}

export interface CaptureSummary {
  totalEvents: number;
  eventsLastDay: number;
  lastEventAt: string | null;
}

export interface ClassificationSummary {
  succeeded: number;
  failed: number;
  awaitingRouting: number;
}

export interface DashboardOverview {
  skills: SkillCount[];
  recentActivity: ActivityItem[];
  capture: CaptureSummary;
  classification: ClassificationSummary;
}

/** Fields shared by every skill entry. */
export interface SkillEntryBase {
  id: string;
  captureEventId: string | null;
  collectionId: string | null;
  sourceUrl: string;
  pageTitle: string;
  confidence: number;
  timesSeen: number;
  occurrences: Array<Record<string, unknown>>;
  createdAt: string;
  lastSeenAt: string;
}

export interface GlossaryTerm extends SkillEntryBase {
  term: string;
  definition: string;
  contextSnippet: string;
}

export interface Citation extends SkillEntryBase {
  quote: string;
  author: string | null;
  workTitle: string | null;
  publisher: string | null;
  publishedDate: string | null;
  formatted: Record<string, string>;
}

export interface Deadline extends SkillEntryBase {
  title: string;
  dueText: string;
  dueDate: string | null;
  kind: string | null;
  contextSnippet: string;
  confirmed: boolean;
}

export interface ContradictionClaim extends SkillEntryBase {
  claim: string;
  topic: string;
}

export interface Contradiction {
  id: string;
  topic: string;
  claimA: string;
  claimB: string;
  sourceAUrl: string;
  sourceBUrl: string;
  explanation: string;
  dismissed: boolean;
  claimAId: string | null;
  claimBId: string | null;
  createdAt: string;
  agreeCount: number;
  disagreeCount: number;
  evidence: ContradictionEvidence[];
}

export interface ContradictionEvidence {
  claim: string;
  sourceUrl: string;
  pageTitle: string;
  stance: string;
  excerpt: string;
}

export interface ReadingCompilerEntry extends SkillEntryBase {
  passage: string;
  dwellMs: number;
  heading: string | null;
}

export interface ProductListing extends SkillEntryBase {
  name: string;
  price: string | null;
  specs: Record<string, string>;
}

export interface NormalizedPrice {
  raw: string | null;
  amount: number | null;
  currency: string | null;
  comparable: boolean;
}

export interface ProductCompareColumn {
  id: string;
  name: string;
  sourceUrl: string;
  pageTitle: string;
  price: NormalizedPrice;
  specs: Record<string, string>;
}

export interface ProductCompare {
  columns: ProductCompareColumn[];
  specKeys: string[];
  lowestPriceIds: string[];
  priceNote: string | null;
}

export interface JobListing extends SkillEntryBase {
  title: string;
  company: string | null;
  salary: string | null;
  requirements: string[];
  applicationDeadline: string | null;
}

export interface ContractFlag extends SkillEntryBase {
  clauseText: string;
  flagReason: string;
  riskLevel: string;
}

export type SkillEntry =
  | GlossaryTerm
  | Citation
  | Deadline
  | ContradictionClaim
  | ReadingCompilerEntry
  | ProductListing
  | JobListing
  | ContractFlag;

export interface Collection {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
}

export interface FormProfile {
  id: string;
  name: string;
  values: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface FormField {
  name: string;
  type: string;
  value: string | null;
  options: string[];
}

export interface FormDocument {
  id: string;
  filename: string;
  sourceUrl: string;
  fields: FormField[];
  fieldCount: number;
  createdAt: string;
}

export interface FieldMatch {
  fieldName: string;
  fieldType: string;
  profileKey: string | null;
  value: string | null;
  confidence: number;
  needsManual: boolean;
  reason: string;
}

export interface DocumentMatch {
  documentId: string;
  filename: string;
  matches: FieldMatch[];
  autoFilled: number;
  needsManual: number;
}

export interface Sighting {
  sourceUrl?: string;
  pageTitle?: string;
  seenAt?: string;
  captureEventId?: string | null;
  confidence?: number;
  contextSnippet?: string | null;
}

export interface WatchedDocument {
  id: string;
  setId: string;
  label: string;
  sourceUrl: string;
  createdAt: string;
  latestSnapshotAt: string | null;
  snapshotCount: number;
}

export interface DocumentDiffEvent {
  id: string;
  setId: string;
  leftDocumentId: string;
  rightDocumentId: string;
  leftLabel: string;
  rightLabel: string;
  unifiedDiff: string;
  changeSummary: string;
  isMeaningful: boolean;
  detectedAt: string;
  viewedAt: string | null;
}

export interface WatchedSet {
  id: string;
  name: string;
  createdAt: string;
  lastViewedAt: string | null;
  documents: WatchedDocument[];
  unreadMeaningful: number;
  latestEventAt: string | null;
}

export interface WatchedSetDetail extends WatchedSet {
  events: DocumentDiffEvent[];
}

export interface UnreadCount {
  unreadMeaningful: number;
}

export interface RecentDocument {
  id: string;
  filename: string;
  sourceUrl: string;
  docType: string;
  summary: string;
  mimeType: string;
  hasFile: boolean;
  createdAt: string;
  lastSeenAt: string;
}

export interface AutoAttachMatch {
  documentId: string;
  filename: string;
  docType: string;
  sourceUrl: string;
  summary: string;
  hasFile: boolean;
  confidence: number;
  reason: string;
}

export interface AutoAttachMatchResponse {
  match: AutoAttachMatch | null;
  candidates: AutoAttachMatch[];
}

export interface PrivacySettings {
  localOnlyDomains: string[];
  defaultDomains: string[];
  effectiveDomains: string[];
  updatedAt: string | null;
  tradeoffNote: string;
}

export interface LocalModeCheck {
  url: string;
  hostname: string;
  localMode: boolean;
  matchedPattern: string | null;
}

export interface Account {
  userId: string;
  displayName: string;
  email: string | null;
  authMode: string;
  createdAt: string;
  updatedAt: string;
  sessionNote: string;
}

export interface LogoutResult {
  ok: boolean;
  detail: string;
}

export interface DigestCard {
  id: string;
  captureEventId: string;
  snippet: string;
  sourceUrl: string;
  pageTitle: string;
  occurredAt: string;
  categories: string[];
  confidence: number;
  reason: string | null;
  reviewStatus: string;
  provider: string;
  model: string;
  cached: boolean;
  fields: Record<string, unknown>;
  group: string;
  groupLabel: string;
}

export interface DigestGroup {
  key: string;
  label: string;
  items: DigestCard[];
}

export interface Digest {
  since: string;
  items: DigestCard[];
  groups: DigestGroup[];
}

export interface AskCitation {
  captureEventId: string;
  sourceUrl: string;
  pageTitle: string;
  snippet: string;
  occurredAt: string | null;
  score: number;
}

export interface AskAnswer {
  question: string;
  answer: string;
  empty: boolean;
  citations: AskCitation[];
}

export interface TrailNode {
  id: string;
  captureEventId: string;
  snippet: string;
  sourceUrl: string;
  pageTitle: string;
  referringUrl: string | null;
  occurredAt: string;
  categories: string[];
  reviewStatus: string | null;
}

export interface TrailEdge {
  source: string;
  target: string;
  kind: string;
}

export interface Trail {
  nodes: TrailNode[];
  edges: TrailEdge[];
  sessionStartedAt: string | null;
  extras: Record<string, unknown>;
}

export interface Brief {
  id: string;
  topic: string;
  markdown: string;
  sourceEventIds: string[];
  deadlineId: string | null;
  createdAt: string;
}

export interface NotificationItem {
  id: string;
  kind: string;
  title: string;
  body: string;
  href: string | null;
  readAt: string | null;
  dismissedAt: string | null;
  createdAt: string;
}

export interface NotificationList {
  items: NotificationItem[];
  unread: number;
}
