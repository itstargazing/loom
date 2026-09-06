import type { PipelineStageView } from "@/lib/home-view";
import { formatCount } from "@/lib/format";

export function PipelineStage({ stage }: { stage: PipelineStageView }) {
  return (
    <section className="loom-glass loom-glass-bright loom-sheen-tr px-xl py-xl">
      <div className="flex flex-col gap-lg sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-sm">
          <span className="loom-badge w-fit">Stage</span>
          <p
            className="loom-display font-display text-stage font-bold tracking-tight text-text-primary"
            aria-label={`Pipeline stage ${stage.numeral} ${stage.name}`}
          >
            {stage.numeral}
          </p>
          <p className="loom-display font-display text-xl font-medium">{stage.name}</p>
        </div>
        <div className="flex max-w-xs flex-col gap-xs text-left font-mono text-xs text-text-secondary sm:items-end sm:text-right">
          <p>
            {stage.waiting === 0
              ? "No signals waiting"
              : `${formatCount(stage.waiting)} waiting`}
          </p>
          <p className="text-text-faint">{stage.description}</p>
        </div>
      </div>
    </section>
  );
}
