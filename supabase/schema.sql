-- Supabase Schema for deepedu.school

-- 用户表（Supabase Auth 自动管理 auth.users，这里只建 profiles）
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  nickname TEXT,
  avatar_url TEXT,
  role TEXT DEFAULT 'student' CHECK (role IN ('student', 'parent', 'teacher')),
  grade TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 知识点表（基于 os-taxonomy）
CREATE TABLE IF NOT EXISTS public.knowledge_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  subject TEXT NOT NULL,
  grade_level TEXT,
  description TEXT,
  prerequisites UUID[] DEFAULT '{}',
  difficulty INTEGER DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
  estimated_minutes INTEGER DEFAULT 15,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 学习记录
CREATE TABLE IF NOT EXISTS public.learning_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  node_id UUID REFERENCES public.knowledge_nodes(id),
  skill_type TEXT NOT NULL,
  score FLOAT DEFAULT 0,
  time_spent_seconds INTEGER DEFAULT 0,
  mastery_probability FLOAT DEFAULT 0.1,
  completed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- BKT 知识状态
CREATE TABLE IF NOT EXISTS public.knowledge_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  node_id UUID NOT NULL REFERENCES public.knowledge_nodes(id),
  p_learned FLOAT DEFAULT 0.1,
  p_guess FLOAT DEFAULT 0.2,
  p_slip FLOAT DEFAULT 0.1,
  p_known FLOAT DEFAULT 0.05,
  last_updated TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, node_id)
);

-- 对话历史
CREATE TABLE IF NOT EXISTS public.chat_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  skill_type TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 英语课程内容
CREATE TABLE IF NOT EXISTS public.english_courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 7),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  tips TEXT,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS Policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.english_courses ENABLE ROW LEVEL SECURITY;

-- 用户只能读写自己的数据
CREATE POLICY "Users can read own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can read own records" ON public.learning_records FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own records" ON public.learning_records FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can read own knowledge states" ON public.knowledge_states FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can upsert own knowledge states" ON public.knowledge_states FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can read own chat" ON public.chat_history FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own chat" ON public.chat_history FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 知识点和课程公开可读
CREATE POLICY "Knowledge nodes are public" ON public.knowledge_nodes FOR SELECT USING (true);
CREATE POLICY "English courses are public" ON public.english_courses FOR SELECT USING (true);

-- 索引
CREATE INDEX idx_learning_records_user ON public.learning_records(user_id, created_at DESC);
CREATE INDEX idx_chat_history_user ON public.chat_history(user_id, created_at DESC);
CREATE INDEX idx_knowledge_states_user ON public.knowledge_states(user_id);
CREATE INDEX idx_knowledge_nodes_subject ON public.knowledge_nodes(subject, grade_level);
