-- Life Ops Feature
-- Tables for daily checklist tracking with categories, recurrence, and streaks
-- Pure CRUD — no AI/Gemini integration

-- ============ Categories ============

CREATE TABLE IF NOT EXISTS lifeops_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  name TEXT NOT NULL,
  color TEXT DEFAULT '#6B7280',
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lifeops_categories_user_id ON lifeops_categories(user_id);

-- ============ Task Definitions ============

CREATE TABLE IF NOT EXISTS lifeops_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  category_id UUID REFERENCES lifeops_categories(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  recurrence_days INTEGER NOT NULL DEFAULT 127, -- bitmask: Mon=1,Tue=2,Wed=4,Thu=8,Fri=16,Sat=32,Sun=64. 127=daily
  sort_order INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lifeops_tasks_user_id ON lifeops_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_lifeops_tasks_category_id ON lifeops_tasks(category_id);

-- ============ Daily Checklist Items ============

CREATE TABLE IF NOT EXISTS lifeops_daily_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  task_id UUID REFERENCES lifeops_tasks(id) ON DELETE CASCADE,
  checklist_date DATE NOT NULL DEFAULT CURRENT_DATE,
  is_completed BOOLEAN DEFAULT false,
  completed_at TIMESTAMPTZ,
  sort_order INTEGER DEFAULT 0,
  -- Denormalized for fast reads
  task_title TEXT NOT NULL,
  category_id UUID,
  category_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, task_id, checklist_date)
);

CREATE INDEX IF NOT EXISTS idx_lifeops_daily_items_user_id ON lifeops_daily_items(user_id);
CREATE INDEX IF NOT EXISTS idx_lifeops_daily_items_date ON lifeops_daily_items(checklist_date);
CREATE INDEX IF NOT EXISTS idx_lifeops_daily_items_user_date ON lifeops_daily_items(user_id, checklist_date);

-- ============ Streaks ============

CREATE TABLE IF NOT EXISTS lifeops_streaks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE,
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  last_completed_date DATE,
  total_perfect_days INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lifeops_streaks_user_id ON lifeops_streaks(user_id);

-- ============ Enable RLS ============

ALTER TABLE lifeops_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE lifeops_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE lifeops_daily_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE lifeops_streaks ENABLE ROW LEVEL SECURITY;

-- ============ RLS Policies (authenticated) ============

-- Categories
CREATE POLICY "Users can view own lifeops categories"
  ON lifeops_categories FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own lifeops categories"
  ON lifeops_categories FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own lifeops categories"
  ON lifeops_categories FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own lifeops categories"
  ON lifeops_categories FOR DELETE
  USING (auth.uid() = user_id);

-- Tasks
CREATE POLICY "Users can view own lifeops tasks"
  ON lifeops_tasks FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own lifeops tasks"
  ON lifeops_tasks FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own lifeops tasks"
  ON lifeops_tasks FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own lifeops tasks"
  ON lifeops_tasks FOR DELETE
  USING (auth.uid() = user_id);

-- Daily Items
CREATE POLICY "Users can view own lifeops daily items"
  ON lifeops_daily_items FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own lifeops daily items"
  ON lifeops_daily_items FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own lifeops daily items"
  ON lifeops_daily_items FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own lifeops daily items"
  ON lifeops_daily_items FOR DELETE
  USING (auth.uid() = user_id);

-- Streaks
CREATE POLICY "Users can view own lifeops streaks"
  ON lifeops_streaks FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own lifeops streaks"
  ON lifeops_streaks FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own lifeops streaks"
  ON lifeops_streaks FOR UPDATE
  USING (auth.uid() = user_id);

-- ============ Anon Policies (API service key) ============

-- Categories
CREATE POLICY "Anon can view all lifeops categories"
  ON lifeops_categories FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert lifeops categories"
  ON lifeops_categories FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update lifeops categories"
  ON lifeops_categories FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete lifeops categories"
  ON lifeops_categories FOR DELETE TO anon
  USING (true);

-- Tasks
CREATE POLICY "Anon can view all lifeops tasks"
  ON lifeops_tasks FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert lifeops tasks"
  ON lifeops_tasks FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update lifeops tasks"
  ON lifeops_tasks FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete lifeops tasks"
  ON lifeops_tasks FOR DELETE TO anon
  USING (true);

-- Daily Items
CREATE POLICY "Anon can view all lifeops daily items"
  ON lifeops_daily_items FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert lifeops daily items"
  ON lifeops_daily_items FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update lifeops daily items"
  ON lifeops_daily_items FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete lifeops daily items"
  ON lifeops_daily_items FOR DELETE TO anon
  USING (true);

-- Streaks
CREATE POLICY "Anon can view all lifeops streaks"
  ON lifeops_streaks FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert lifeops streaks"
  ON lifeops_streaks FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update lifeops streaks"
  ON lifeops_streaks FOR UPDATE TO anon
  USING (true);
