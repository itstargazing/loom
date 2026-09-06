import { EXTRA_SKILL_LINKS, SKILL_VIEWS, skillPageExists } from "./skills";
import type {
  Account,
  Contradiction,
  DashboardOverview,
  Deadline,
  PrivacySettings,
  WatchedSet,
} from "./types";

export type PipelineStageId = 1 | 2 | 3;

export interface PipelineStageView {
  id: PipelineStageId;
  numeral: string;
  name: string;
  waiting: number;
  description: string;
}

export interface AttentionItem {
  href: string;
  label: string;
}

export interface HomeView {
  displayName: string;
  empty: boolean;
  headline: [string, string];
  stage: PipelineStageView;
  signalsWoven: number;
  signalsLastDay: number;
  classified: number;
  localOnlyDomains: number;
  localOnlyActive: boolean;
  unresolved: AttentionItem[];
  routeNext: AttentionItem[];
  facts: string;
}

const CLASSIFIER_FACTS =
  "Classification defaults to an offline keyword stub. It returns none unless a highlight or copy looks like a term, quote, date, product, or job. Local-only domains never call a cloud model. Events still sync to your LOOM backend.";

function firstName(displayName: string): string {
  const trimmed = displayName.trim();
  if (!trimmed) return "there";
  return trimmed.split(/\s+/)[0] ?? trimmed;
}

export function resolvePipelineStage(
  overview: DashboardOverview,
): PipelineStageView {
  const pendingClassify = Math.max(
    0,
    overview.capture.totalEvents -
      overview.classification.succeeded -
      overview.classification.failed,
  );
  const waitingRoute = overview.classification.awaitingRouting;

  if (waitingRoute > 0) {
    return {
      id: 3,
      numeral: "03",
      name: "Route",
      waiting: waitingRoute,
      description:
        "Classified events are waiting to be written into a skill store.",
    };
  }

  if (pendingClassify > 0) {
    return {
      id: 2,
      numeral: "02",
      name: "Classify",
      waiting: pendingClassify,
      description:
        "Captured events are in the heuristic classifier before anything is filed.",
    };
  }

  return {
    id: 1,
    numeral: "01",
    name: "Capture",
    waiting: 0,
    description: overview.capture.totalEvents
      ? "The pipeline is quiet. New highlights, copies, and dwells will enter here."
      : "Nothing has arrived yet. Leave Highlights on and select a term, then sync.",
  };
}

function skillHref(slug: string): string {
  if (slug === "contradiction-claims") return "/skills/contradictions";
  return `/skills/${slug}`;
}

export function buildHomeView({
  overview,
  account,
  privacy,
  contradictions,
  deadlines,
  watchedSets,
}: {
  overview: DashboardOverview | null;
  account: Account | null;
  privacy: PrivacySettings | null;
  contradictions: Contradiction[] | null;
  deadlines: Deadline[] | null;
  watchedSets: WatchedSet[] | null;
}): HomeView {
  const empty = !overview || overview.capture.totalEvents === 0;
  const name = firstName(account?.displayName ?? "there");
  const localOnlyDomains = privacy?.effectiveDomains.length ?? 0;

  const unresolved: AttentionItem[] = [];
  if (overview && overview.classification.failed > 0) {
    unresolved.push({
      href: "/",
      label: `${overview.classification.failed} classification${
        overview.classification.failed === 1 ? "" : "s"
      } failed`,
    });
  }
  const openContradictions = (contradictions ?? []).filter((row) => !row.dismissed);
  if (openContradictions.length > 0) {
    unresolved.push({
      href: skillHref("contradictions"),
      label: `${openContradictions.length} open contradiction${
        openContradictions.length === 1 ? "" : "s"
      }`,
    });
  }
  const openDeadlines = (deadlines ?? []).filter((row) => !row.confirmed);
  if (openDeadlines.length > 0) {
    unresolved.push({
      href: skillHref("deadlines"),
      label: `${openDeadlines.length} unconfirmed deadline${
        openDeadlines.length === 1 ? "" : "s"
      }`,
    });
  }
  const unreadDiffs = (watchedSets ?? []).reduce(
    (sum, set) => sum + set.unreadMeaningful,
    0,
  );
  if (unreadDiffs > 0) {
    unresolved.push({
      href: skillHref("live-doc-diff"),
      label: `${unreadDiffs} unread document change${unreadDiffs === 1 ? "" : "s"}`,
    });
  }

  const routeNext: AttentionItem[] = [];
  if (overview && overview.classification.awaitingRouting > 0) {
    routeNext.push({
      href: "/",
      label: `${overview.classification.awaitingRouting} classified event${
        overview.classification.awaitingRouting === 1 ? "" : "s"
      } waiting to file`,
    });
  }

  const populated = (overview?.skills ?? [])
    .filter((skill) => skill.count > 0)
    .filter(
      (skill) =>
        skillPageExists(skill.skill) || skill.skill === "contradiction-claims",
    )
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);
  for (const skill of populated) {
    routeNext.push({
      href: skillHref(skill.skill),
      label: `${skill.label} · ${skill.count}`,
    });
  }

  if (routeNext.length === 0) {
    const firstSkill = SKILL_VIEWS[0] ?? EXTRA_SKILL_LINKS[0];
    if (firstSkill) {
      routeNext.push({
        href: skillHref("slug" in firstSkill ? firstSkill.slug : "glossary"),
        label: "Highlights are on by default. Select a short term, then sync.",
      });
    }
  }

  return {
    displayName: name,
    empty,
    headline: empty
      ? ["Nothing captured yet", "Browse with Highlights on, then sync."]
      : [`${name}'s weave`, "Capture is filing what you linger on."],
    stage: overview
      ? resolvePipelineStage(overview)
      : {
          id: 1,
          numeral: "01",
          name: "Capture",
          waiting: 0,
          description:
            "The backend did not answer. Capture still runs in the extension until sync can land.",
        },
    signalsWoven: overview?.capture.totalEvents ?? 0,
    signalsLastDay: overview?.capture.eventsLastDay ?? 0,
    classified: overview?.classification.succeeded ?? 0,
    localOnlyDomains,
    localOnlyActive: localOnlyDomains > 0,
    unresolved,
    routeNext,
    facts: CLASSIFIER_FACTS,
  };
}
