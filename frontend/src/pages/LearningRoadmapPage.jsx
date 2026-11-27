import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Compass,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import {
  fetchLearningRoadmap,
  generateLearningRoadmap,
} from "../api/sessions.api.js";
import { extractApiError } from "../utils/apiErrors.js";
import { Badge } from "../components/ui/Badge.jsx";
import { Button } from "../components/ui/Button.jsx";
import { Card } from "../components/ui/Card.jsx";
import { RoadmapStepCard } from "../components/roadmap/RoadmapStepCard.jsx";
import { SkillGapOverview } from "../components/roadmap/SkillGapOverview.jsx";

function RoadmapSkeleton() {
  return (
    <div className="animate-pulse space-y-6" aria-label="Loading learning roadmap">
      <div className="h-36 rounded-2xl bg-slate-200/80" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="h-32 rounded-xl bg-slate-200/80" />
        <div className="h-32 rounded-xl bg-slate-200/80" />
        <div className="h-32 rounded-xl bg-slate-200/80" />
      </div>
      <div className="h-64 rounded-xl bg-slate-200/80" />
    </div>
  );
}

export function LearningRoadmapPage() {
  const { id } = useParams();
  const location = useLocation();
  const initialRoadmap = location.state?.roadmap || null;

  const [roadmapRecord, setRoadmapRecord] = useState(initialRoadmap);
  const [isLoading, setIsLoading] = useState(!initialRoadmap);
  const [isMissing, setIsMissing] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [actionError, setActionError] = useState("");

  const loadRoadmap = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setIsMissing(false);
    setLoadError("");

    try {
      const data = await fetchLearningRoadmap(id);
      setRoadmapRecord(data);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 404) {
        setIsMissing(true);
        setRoadmapRecord(null);
      } else {
        const parsed = extractApiError(
          err,
          "Unable to load your learning roadmap. Please try again."
        );
        setLoadError(parsed.message);
      }
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!initialRoadmap) {
      loadRoadmap();
    }
  }, [initialRoadmap, loadRoadmap]);

  async function handleGenerate({ regenerate = false } = {}) {
    if (!id || isGenerating) return;
    setIsGenerating(true);
    setActionError("");

    try {
      const data = await generateLearningRoadmap(id, { regenerate });
      setRoadmapRecord(data);
      setIsMissing(false);
    } catch (err) {
      const parsed = extractApiError(
        err,
        "Unable to generate learning roadmap. Please try again."
      );
      setActionError(parsed.message);
    } finally {
      setIsGenerating(false);
    }
  }

  if (isLoading) {
    return <RoadmapSkeleton />;
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-xl py-12">
        <Card className="p-8 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-rose-200 bg-rose-50 text-rose-700">
            <AlertCircle className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="mt-4 font-display text-xl font-bold text-foreground">
            Could Not Load Learning Roadmap
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-foreground-secondary">
            {loadError}
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Button type="button" variant="primary" size="md" onClick={loadRoadmap}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              <span>Retry</span>
            </Button>
            <Link to={`/sessions/${id}/summary`}>
              <Button variant="secondary" size="md">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                <span>Back to Interview Summary</span>
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  if (isMissing || !roadmapRecord) {
    return (
      <div className="mx-auto max-w-xl py-12">
        <Card className="p-8 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-primary/25 bg-primary-subtle text-primary">
            <Compass className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="mt-4 font-display text-xl font-bold text-foreground">
            No Learning Roadmap Generated Yet
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-foreground-secondary">
            Generate a personalized, priority-ordered study plan based on your interview performance and identified skill gaps.
          </p>

          {actionError ? (
            <div
              role="alert"
              className="mt-4 flex items-center justify-center gap-2 rounded-lg border border-destructive/25 bg-destructive-bg p-3 text-xs text-destructive"
            >
              <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{actionError}</span>
            </div>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Button
              type="button"
              variant="primary"
              size="md"
              isLoading={isGenerating}
              disabled={isGenerating}
              onClick={() => handleGenerate({ regenerate: false })}
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  <span>Generating Learning Roadmap...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  <span>Generate Learning Roadmap</span>
                </>
              )}
            </Button>
            <Link to={`/sessions/${id}/summary`}>
              <Button variant="secondary" size="md">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                <span>Back to Interview Summary</span>
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const roadmap = roadmapRecord.roadmap_json || {};
  const skillGaps = Array.isArray(roadmapRecord.skill_gaps_json)
    ? roadmapRecord.skill_gaps_json
    : [];
  const steps = Array.isArray(roadmap.learning_steps) ? roadmap.learning_steps : [];

  return (
    <div className="space-y-8 pb-12">
      {/* Header Banner */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#070D19] via-[#0B1528] to-[#0F1D3A] p-6 text-white shadow-lg sm:p-8">
        <div className="relative flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div className="space-y-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="teal">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                <span>Personalized Learning Roadmap</span>
              </Badge>
              {roadmap.estimated_hours ? (
                <Badge tone="neutral">
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  <span>Est. {roadmap.estimated_hours} hrs</span>
                </Badge>
              ) : null}
            </div>

            <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
              {roadmap.title || "Personalized Learning Roadmap"}
            </h1>
            {roadmap.overview ? (
              <p className="max-w-2xl text-sm leading-relaxed text-slate-300">
                {roadmap.overview}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <Link to={`/sessions/${id}/summary`}>
              <Button
                variant="secondary"
                size="md"
                className="border-white/20 bg-white/10 text-white hover:bg-white/20"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                <span>Back to Interview Summary</span>
              </Button>
            </Link>

            <Button
              type="button"
              variant="primary"
              size="md"
              isLoading={isGenerating}
              disabled={isGenerating}
              onClick={() => handleGenerate({ regenerate: true })}
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  <span>Regenerating...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" aria-hidden="true" />
                  <span>Regenerate Roadmap</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </section>

      {actionError ? (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-destructive/25 bg-destructive-bg p-4 text-sm text-destructive"
        >
          <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{actionError}</span>
        </div>
      ) : null}

      {/* Skill-Gap Overview */}
      <SkillGapOverview skillGaps={skillGaps} />

      {/* Ordered Learning Steps */}
      <section aria-label="Ordered learning steps" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-foreground">
            Ordered Study Plan
          </h2>
          <Badge tone="primary">
            {steps.length} {steps.length === 1 ? "Step" : "Steps"}
          </Badge>
        </div>

        {steps.length > 0 ? (
          <div className="space-y-4">
            {steps.map((step, idx) => (
              <RoadmapStepCard key={step.order || idx} step={step} />
            ))}
          </div>
        ) : (
          <Card className="p-6 text-center text-sm text-foreground-secondary">
            No learning steps were returned for this roadmap. Try regenerating your roadmap.
          </Card>
        )}
      </section>
    </div>
  );
}

export default LearningRoadmapPage;

