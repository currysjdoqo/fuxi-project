<template>
  <div class="auth-page login-page">
    <div class="grain"></div>
    <div class="auth-stage">
      <section class="auth-hero">
        <p class="hero-kicker">EXERCISE STUDIO</p>
        <h1>把练习这件事，做得更像真正的备考。</h1>
        <p class="hero-text">
          题库、错题、复习记录放在同一套节奏里。登录后继续上一轮的练习状态，不需要重新整理现场。
        </p>

        <div class="hero-panels">
          <article class="hero-panel panel-primary">
            <span class="panel-label">Today</span>
            <strong>专注做题，不被界面打断</strong>
            <p>更克制的配色，更明确的层级，更像工具，不像套模板。</p>
          </article>
          <article class="hero-panel panel-secondary">
            <span class="metric">01</span>
            <p>支持题库管理、随机练习、错题回看与学习计划联动。</p>
          </article>
        </div>
      </section>

      <section class="auth-card">
        <div class="card-top">
          <p class="eyebrow">登录</p>
          <h2>欢迎回来</h2>
          <p class="card-copy">输入账号和密码，继续你的练习。</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" class="auth-form">
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              size="large"
              clearable
              :prefix-icon="User"
              autocomplete="username"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              size="large"
              show-password
              :prefix-icon="Lock"
              autocomplete="current-password"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-form-item>
            <el-button class="submit-btn" type="primary" size="large" :loading="loading" @click="handleLogin">
              {{ loading ? '登录中...' : '进入系统' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="divider">
          <span>还没有账号？</span>
        </div>

        <button class="switch-link" type="button" @click="router.push('/auth/register')">
          创建新账号
        </button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { login } from '../api'
import { clearLegacySharedAuth, saveAuthSession } from '../utils/authStorage'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const result = await login(form.username.trim(), form.password.trim())
    saveAuthSession({
      token: result.token,
      username: result.username,
      userId: result.user_id,
      userCode: result.user_code || ''
    })
    clearLegacySharedAuth()
    ElMessage.success('登录成功')
    router.replace('/')
  } catch (error) {
    const status = error?.response?.status
    const detail = error?.response?.data?.detail
    if (status === 404 || detail === 'USER_NOT_FOUND') {
      ElMessage.warning('用户不存在，请先注册')
      router.push('/auth/register')
      return
    }
    ElMessage.error('用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  --bg: #f4efe6;
  --paper: rgba(255, 251, 245, 0.86);
  --paper-strong: rgba(255, 252, 248, 0.96);
  --ink: #1f2933;
  --muted: #5f6b76;
  --line: rgba(31, 41, 51, 0.1);
  --accent: #b85c38;
  --accent-dark: #8d3f1f;
  --accent-soft: rgba(184, 92, 56, 0.12);
}

.auth-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(184, 92, 56, 0.14), transparent 28%),
    radial-gradient(circle at 80% 20%, rgba(29, 78, 216, 0.08), transparent 24%),
    linear-gradient(135deg, #f1e7d8 0%, #f8f4ec 35%, #ebe3d7 100%);
}

.grain {
  position: absolute;
  inset: 0;
  opacity: 0.22;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: radial-gradient(circle at center, black, transparent 88%);
}

.auth-stage {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  max-width: 1240px;
  margin: 0 auto;
  padding: 40px 28px;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) 420px;
  gap: 28px;
  align-items: stretch;
}

.auth-hero {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 52px;
  border-radius: 32px;
  background: linear-gradient(160deg, rgba(40, 32, 27, 0.96) 0%, rgba(63, 45, 36, 0.9) 100%);
  color: #f8f1e8;
  box-shadow: 0 24px 70px rgba(58, 37, 27, 0.18);
}

.hero-kicker {
  margin: 0 0 18px;
  font-size: 12px;
  letter-spacing: 0.28em;
  color: rgba(248, 241, 232, 0.68);
}

.auth-hero h1 {
  max-width: 680px;
  margin: 0;
  font-family: Georgia, 'Times New Roman', 'Songti SC', serif;
  font-size: clamp(42px, 5vw, 72px);
  line-height: 1.02;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.hero-text {
  max-width: 560px;
  margin: 24px 0 0;
  font-size: 17px;
  line-height: 1.9;
  color: rgba(248, 241, 232, 0.8);
}

.hero-panels {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(220px, 0.8fr);
  gap: 18px;
  margin-top: 40px;
}

.hero-panel {
  border-radius: 24px;
  padding: 24px;
  backdrop-filter: blur(10px);
}

.panel-primary {
  background: rgba(255, 247, 238, 0.1);
  border: 1px solid rgba(255, 247, 238, 0.18);
}

.panel-secondary {
  display: grid;
  align-content: space-between;
  background: linear-gradient(180deg, rgba(184, 92, 56, 0.22), rgba(184, 92, 56, 0.08));
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.panel-label {
  display: inline-flex;
  margin-bottom: 14px;
  font-size: 11px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(248, 241, 232, 0.62);
}

.hero-panel strong {
  display: block;
  margin-bottom: 10px;
  font-size: 22px;
  line-height: 1.35;
}

.hero-panel p {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: rgba(248, 241, 232, 0.76);
}

.metric {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 56px;
  line-height: 1;
}

.auth-card {
  align-self: center;
  padding: 38px 34px 32px;
  border-radius: 28px;
  background: var(--paper-strong);
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow: 0 18px 60px rgba(52, 47, 42, 0.12);
  backdrop-filter: blur(18px);
}

.card-top {
  margin-bottom: 26px;
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: var(--accent);
}

.card-top h2 {
  margin: 0;
  font-size: 32px;
  color: var(--ink);
  letter-spacing: -0.03em;
}

.card-copy {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.auth-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.auth-form :deep(.el-input__wrapper) {
  min-height: 54px;
  border-radius: 18px;
  background: var(--paper);
  box-shadow: 0 0 0 1px rgba(108, 93, 77, 0.12) inset;
}

.auth-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(184, 92, 56, 0.34) inset;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(184, 92, 56, 0.76) inset;
}

.auth-form :deep(.el-input__inner) {
  font-size: 15px;
}

.submit-btn {
  width: 100%;
  height: 54px;
  border: none;
  border-radius: 18px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
  box-shadow: 0 14px 30px rgba(184, 92, 56, 0.24);
}

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0 14px;
  color: #8a7767;
  font-size: 13px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}

.switch-link {
  width: 100%;
  height: 50px;
  border-radius: 16px;
  border: 1px solid rgba(184, 92, 56, 0.18);
  background: var(--accent-soft);
  color: var(--accent-dark);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.switch-link:hover {
  background: rgba(184, 92, 56, 0.16);
  transform: translateY(-1px);
}

@media (max-width: 1080px) {
  .auth-stage {
    grid-template-columns: 1fr;
  }

  .auth-hero {
    min-height: 520px;
  }

  .auth-card {
    max-width: 520px;
    width: 100%;
    justify-self: center;
  }
}

@media (max-width: 720px) {
  .auth-stage {
    padding: 16px;
    gap: 16px;
  }

  .auth-hero,
  .auth-card {
    padding: 26px 22px;
    border-radius: 24px;
  }

  .auth-hero {
    min-height: auto;
  }

  .hero-panels {
    grid-template-columns: 1fr;
  }

  .auth-hero h1 {
    font-size: 42px;
  }

  .card-top h2 {
    font-size: 28px;
  }
}
</style>
