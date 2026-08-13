// Types mirroring the FastAPI backend contract exactly (resume_agent/api.py + models.py).

export interface ResumeBullet {
  id: string;
  employer: string;
  role: string;
  start_date: string;
  end_date: string | null;
  text: string;
  skills: string[];
  seniority_signal: string | null;
  quantified_outcome: string | null;
  source_paragraph_index: number | null;
}

export interface UploadResponse {
  bullets: ResumeBullet[];
  has_docx: boolean;
}

export type JDCategory =
  | "hard_skill"
  | "soft_skill"
  | "experience_years"
  | "domain_knowledge";

export type JDImportance = "must_have" | "nice_to_have";

export interface JDRequirement {
  text: string;
  category: JDCategory;
  importance: JDImportance;
  implied_skills: string[];
}

export interface ParsedJD {
  role_title: string;
  seniority_level: string;
  requirements: JDRequirement[];
}

export type CoverageLevel = 0 | 1 | 2;

export interface MatchResult {
  requirement: string;
  coverage: CoverageLevel;
  matched_bullet_ids: string[];
  reasoning: string;
}

export interface ScoreReport {
  keyword_coverage_pct: number;
  substantive_fit_score: number;
  must_have_gaps: string[];
  per_requirement: MatchResult[];
}

export type ChangeType = "rewrite" | "keyword_injection" | "tech_swap";

export interface ProposedChange {
  id: string;
  bullet_id: string;
  employer: string;
  role: string;
  change_type: ChangeType;
  original_text: string;
  proposed_text: string;
  rationale: string;
  related_requirement: string | null;
  requires_confirmation: boolean;
  confirmation_prompt: string | null;
}

export interface AnalyzeResponse {
  parsed_jd: ParsedJD;
  report: ScoreReport;
  proposed_changes: ProposedChange[];
}

export interface FinalizeRequestBullet {
  bullet_id: string;
  text: string;
}

export interface FinalizeRequest {
  bullets: FinalizeRequestBullet[];
}

export interface FinalizeResponse {
  docx_url: string | null;
  pdf_url: string | null;
  edited_count: number;
  skipped_count: number;
}

export type Step = "upload" | "jd" | "review" | "done";
