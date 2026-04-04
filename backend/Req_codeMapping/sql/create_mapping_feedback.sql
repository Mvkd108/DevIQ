CREATE TABLE IF NOT EXISTS mapping_feedback (
  commit_id            TEXT PRIMARY KEY,
  feedback_type        TEXT NOT NULL CHECK (feedback_type IN ('approved', 'rejected', 'reassigned', 'cleared')),
  predicted_issue_id   TEXT,
  corrected_issue_id   TEXT,
  reviewed_by          TEXT NOT NULL,
  reviewed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mapping_feedback_reviewed_at
  ON mapping_feedback (reviewed_at DESC);

CREATE OR REPLACE FUNCTION update_mapping_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mapping_feedback_updated_at ON mapping_feedback;
CREATE TRIGGER trg_mapping_feedback_updated_at
  BEFORE UPDATE ON mapping_feedback
  FOR EACH ROW EXECUTE FUNCTION update_mapping_feedback_updated_at();
