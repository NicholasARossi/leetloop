-- Telegram bot user links
-- Maps Telegram chat IDs to LeetLoop user IDs

CREATE TABLE IF NOT EXISTS telegram_user_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_chat_id BIGINT NOT NULL UNIQUE,
  user_id UUID NOT NULL,
  telegram_username TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telegram_user_links_chat_id ON telegram_user_links(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_telegram_user_links_user_id ON telegram_user_links(user_id);

-- Enable RLS
ALTER TABLE telegram_user_links ENABLE ROW LEVEL SECURITY;

-- Anon policies (API service key manages all links)
CREATE POLICY "Anon can view all telegram links"
  ON telegram_user_links FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert telegram links"
  ON telegram_user_links FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update telegram links"
  ON telegram_user_links FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete telegram links"
  ON telegram_user_links FOR DELETE TO anon
  USING (true);
