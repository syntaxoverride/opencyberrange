-- Make user deletion possible: give every FK referencing users(id) an explicit
-- ON DELETE rule. Without one, Postgres defaults to NO ACTION and any user who
-- has SOC work, a lab session, or an invite code cannot be deleted at all.
--
-- CASCADE  = the row belongs to the user and is meaningless without them
-- SET NULL = the row has independent value, keep it but drop the identity link
--
-- courses.instructor_id is deliberately NOT changed: the delete endpoint removes
-- an instructor's courses explicitly, and a DB-level cascade would silently
-- destroy courses and their enrollments from any future delete path.
DO $$
DECLARE
  t RECORD;
  cname TEXT;
  fixed INT := 0;
  skipped INT := 0;
BEGIN
  FOR t IN
    SELECT * FROM (VALUES
      ('lab_sessions',          'user_id',       'CASCADE'),
      ('lab_sessions',          'impersonated_by','SET NULL'),
      ('lab_completions',       'user_id',       'CASCADE'),
      ('flag_attempts',         'user_id',       'CASCADE'),
      ('wireguard_configs',     'user_id',       'CASCADE'),
      ('revoked_tokens',        'user_id',       'CASCADE'),
      ('invite_codes',          'created_by',    'CASCADE'),
      ('invite_codes',          'used_by',       'SET NULL'),
      ('template_instances',    'instructor_id', 'CASCADE'),
      ('studio_pending_review', 'instructor_id', 'CASCADE'),
      ('exercise_gen_jobs',     'instructor_id', 'CASCADE'),
      ('soc_triage_sessions',   'user_id',       'CASCADE'),
      ('soc_hitl_reviews',      'user_id',       'CASCADE'),
      ('soc_hitl_reviews',      'graded_by',     'SET NULL'),
      -- Tables that exist on some instances only. Each is skipped where absent,
      -- so this block is a no-op on an instance that never had them.
      --
      -- soc_exercise_* are ORPHANS on the dev database: leftovers from the
      -- retired SOC Analyst / SOC Engineer tracks. No model on main defines
      -- them, yet their constraints still block user deletion, because a
      -- constraint does not care whether any code uses the table.
      ('soc_exercises',             'instructor_id', 'CASCADE'),
      ('soc_exercise_actions',      'user_id',       'CASCADE'),
      ('soc_exercise_roles',        'user_id',       'CASCADE'),
      ('soc_exercise_deliverables', 'submitted_by',  'CASCADE'),
      ('soc_exercise_deliverables', 'graded_by',     'SET NULL'),
      ('soc_exercise_scores',       'graded_by',     'SET NULL'),
      ('soc_exercise_events',       'detected_by',   'SET NULL'),
      -- llmr_* belong to the LLM Range work. Their models live on the
      -- llm-range-spike branch and declare bare ForeignKey("users.id"), so they
      -- reproduce this same defect. Fixing the constraints here keeps dev
      -- deletable; the models still need ondelete before that branch merges.
      ('llmr_seats',            'user_id',       'CASCADE'),
      ('llmr_findings',         'user_id',       'CASCADE'),
      ('llmr_defense_configs',  'submitted_by',  'SET NULL')
    ) AS s(tbl, col, act)
  LOOP
    SELECT tc.constraint_name INTO cname
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = t.tbl
      AND kcu.column_name = t.col
      AND ccu.table_name = 'users'
    LIMIT 1;

    IF cname IS NULL THEN
      RAISE NOTICE 'SKIP  %.% (no FK to users found)', t.tbl, t.col;
      skipped := skipped + 1;
      CONTINUE;
    END IF;

    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', t.tbl, cname);
    EXECUTE format(
      'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES users(id) ON DELETE %s',
      t.tbl, cname, t.col, t.act);
    RAISE NOTICE 'FIXED %.% -> ON DELETE %', t.tbl, t.col, t.act;
    fixed := fixed + 1;
  END LOOP;

  RAISE NOTICE '---- % constraints fixed, % skipped ----', fixed, skipped;
END $$;
