-- ============================================================
-- AXIOM OS — Lamora Healthcare  
-- Supabase Schema — run in Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── PROFILES ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email TEXT,
  full_name TEXT,
  role TEXT DEFAULT 'user',
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, email, full_name)
  VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ── LEADS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  organisation TEXT,
  email TEXT,
  phone TEXT,
  service_type TEXT,
  service_category TEXT,
  stage TEXT DEFAULT 'New Lead',
  urgency TEXT DEFAULT 'medium',
  lead_score INTEGER DEFAULT 0,
  source TEXT,
  location TEXT,
  buyer_type TEXT,
  snippet TEXT,
  notes TEXT,
  tags TEXT[] DEFAULT '{}',
  pipeline_value NUMERIC DEFAULT 0,
  assigned_to TEXT,
  last_contacted TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own leads" ON leads FOR ALL USING (auth.uid() = user_id);

-- ── RELATIONSHIPS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS relationships (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  short_name TEXT,
  type TEXT NOT NULL,
  contact_name TEXT,
  role TEXT,
  email TEXT,
  phone TEXT,
  last_referral TIMESTAMPTZ,
  last_contact TIMESTAMPTZ,
  referrals_total INTEGER DEFAULT 0,
  referrals_90_days INTEGER DEFAULT 0,
  referral_trend TEXT DEFAULT 'stable',
  health_score INTEGER DEFAULT 50,
  contract_expiry TIMESTAMPTZ,
  framework TEXT,
  notes TEXT,
  pending_action TEXT,
  action_due TIMESTAMPTZ,
  urgency TEXT DEFAULT 'medium',
  tags TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own relationships" ON relationships FOR ALL USING (auth.uid() = user_id);

-- ── RELATIONSHIP ACTIONS (log) ───────────────────────────────
CREATE TABLE IF NOT EXISTS relationship_actions (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
  action_type TEXT,
  subject TEXT,
  message TEXT,
  talking_points TEXT[],
  risk TEXT,
  next_step TEXT,
  actioned_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE relationship_actions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own actions" ON relationship_actions FOR ALL USING (auth.uid() = user_id);

-- ── TASKS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'pending',
  priority TEXT DEFAULT 'medium',
  due_date TIMESTAMPTZ,
  related_type TEXT,
  related_id UUID,
  assigned_to TEXT,
  tags TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own tasks" ON tasks FOR ALL USING (auth.uid() = user_id);

-- ── SCRAPER JOBS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scraper_jobs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'pending',
  keywords TEXT[],
  locations TEXT[],
  sources TEXT[],
  max_results INTEGER DEFAULT 20,
  results_count INTEGER DEFAULT 0,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE scraper_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own scraper jobs" ON scraper_jobs FOR ALL USING (auth.uid() = user_id);

-- ── SCRAPER RESULTS ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scraper_results (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id UUID REFERENCES scraper_jobs(id) ON DELETE CASCADE,
  source TEXT,
  page_url TEXT,
  title TEXT,
  snippet TEXT,
  service_needed TEXT,
  urgency TEXT,
  location TEXT,
  buyer_type TEXT,
  lead_score INTEGER DEFAULT 0,
  contact_method TEXT,
  status TEXT DEFAULT 'pending',
  ai_analysis TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE scraper_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own scraper results" ON scraper_results FOR ALL USING (auth.uid() = user_id);

-- ── EMAIL OUTREACH ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_outreach (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  relationship_id UUID REFERENCES relationships(id) ON DELETE SET NULL,
  to_email TEXT NOT NULL,
  to_name TEXT,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT DEFAULT 'draft',
  sent_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  replied_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE email_outreach ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own emails" ON email_outreach FOR ALL USING (auth.uid() = user_id);

-- ── AGENT LOGS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_logs (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  agent_name TEXT NOT NULL,
  status TEXT DEFAULT 'running',
  input JSONB,
  output JSONB,
  duration_ms INTEGER,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own agent logs" ON agent_logs FOR ALL USING (auth.uid() = user_id);

-- ── STAFF ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS staff (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  role TEXT,
  email TEXT,
  phone TEXT,
  contract_type TEXT,
  status TEXT DEFAULT 'active',
  location TEXT,
  skills TEXT[] DEFAULT '{}',
  availability JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE staff ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own staff" ON staff FOR ALL USING (auth.uid() = user_id);

-- ── ROTA ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rota (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  staff_id UUID REFERENCES staff(id) ON DELETE CASCADE,
  shift_date DATE NOT NULL,
  shift_start TIME NOT NULL,
  shift_end TIME NOT NULL,
  client_name TEXT,
  location TEXT,
  service_type TEXT,
  status TEXT DEFAULT 'scheduled',
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE rota ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own rota" ON rota FOR ALL USING (auth.uid() = user_id);
