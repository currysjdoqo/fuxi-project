<template>
  <div class="auth-page register-page">
    <div class="grain"></div>
    <div class="auth-stage">
      <section class="auth-hero">
        <p class="hero-kicker">NEW ACCOUNT</p>
        <h1>先把学习空间搭好，再开始刷题。</h1>
        <p class="hero-text">
          创建账号后，题库、练习记录、错题与计划都会归到同一身份下，后续整理和复盘会更顺手。
        </p>

        <div class="hero-grid">
          <article class="hero-note large">
            <span class="note-index">A</span>
            <div>
              <strong>一个账号，一套练习轨迹</strong>
              <p>避免题目、记录和错题状态互相混乱，后续统计也更可靠。</p>
            </div>
          </article>
          <article class="hero-note">
            <span class="note-index">B</span>
            <div>
              <strong>更适合长期复习</strong>
              <p>从导题到随机练习，再到回看错题，流程能接上。</p>
            </div>
          </article>
        </div>
      </section>

      <section class="auth-card">
        <div class="card-top">
          <p class="eyebrow">注册</p>
          <h2>创建账号</h2>
          <p class="card-copy">填写基础信息，创建你的练习空间。</p>
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
              placeholder="密码，至少 6 位"
              size="large"
              show-password
              :prefix-icon="Lock"
              autocomplete="new-password"
            />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input
              v-model="form.confirmPassword"
              type="password"
              placeholder="再次输入密码"
              size="large"
              show-password
              :prefix-icon="Lock"
              autocomplete="new-password"
              @keyup.enter="handleRegister"
            />
          </el-form-item>

          <el-form-item>
            <el-button class="submit-btn" type="primary" size="large" :loading="loading" @click="handleRegister">
              {{ loading ? '创建中...' : '立即创建' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="divider">
          <span>已经有账号</span>
        </div>

        <button class="switch-link" type="button" @click="router.push('/auth/login')">
          返回登录
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
import { register } from '../api'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const validatePass = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度需在 2 到 20 之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ],
  confirmPassword: [{ validator: validatePass, trigger: 'blur' }]
}

const handleRegister = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const result = await register(form.username.trim(), form.password.trim())
    localStorage.setItem('auth_token', result.token)
    localStorage.setItem('auth_username', result.username)
    sessionStorage.setItem('auth_session_ok', '1')
    ElMessage.success('注册成功')
    router.replace('/')
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '注册失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  --bg: #eef1eb;
  --paper: rgba(246, 249, 242, 0.82);
  --paper-strong: rgba(251, 253, 248, 0.95);
  --ink: #203127;
  --muted: #58705f;
  --line: rgba(32, 49, 39, 0.1);
  --accent: #2f7a59;
  --accent-dark: #215640;
  --accent-soft: rgba(47, 122, 89, 0.12);
}

.auth-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 10% 15%, rgba(47, 122, 89, 0.18), transparent 28%),
    radial-gradient(circle at 88% 18%, rgba(15, 23, 42, 0.08), transparent 20%),
    linear-gradient(135deg, #eef3ea 0%, #f7f7f2 46%, #e7ede4 100%);
}

.grain {
  position: absolute;
  inset: 0;
  opacity: 0.18;
  pointer-events: none;
  background-image:
    radial-gradient(circle at 1px 1px, rgba(32, 49, 39, 0.08) 1px, transparent 0);
  background-size: 14px 14px;
}

.auth-stage {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  max-width: 1240px;
  margin: 0 auto;
  padding: 40px 28px;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) 430px;
  gap: 28px;
  align-items: stretch;
}

.auth-hero {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 52px;
  border-radius: 32px;
  color: #eff7f1;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.08), transparent 22%),
    linear-gradient(160deg, rgba(28, 56, 44, 0.96) 0%, rgba(36, 82, 61, 0.94) 100%);
  box-shadow: 0 24px 70px rgba(33, 86, 64, 0.16);
}

.hero-kicker {
  margin: 0 0 18px;
  font-size: 12px;
  letter-spacing: 0.28em;
  color: rgba(239, 247, 241, 0.66);
}

.auth-hero h1 {
  max-width: 720px;
  margin: 0;
  font-family: Georgia, 'Times New Roman', 'Songti SC', serif;
  font-size: clamp(42px, 5vw, 72px);
  line-height: 1.04;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.hero-text {
  max-width: 560px;
  margin: 24px 0 0;
  font-size: 17px;
  line-height: 1.9;
  color: rgba(239, 247, 241, 0.8);
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 18px;
  margin-top: 40px;
}

.hero-note {
  display: flex;
  gap: 16px;
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.hero-note.large {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.06));
}

.note-index {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
  color: #163425;
  background: #d9efdf;
}

.hero-note strong {
  display: block;
  margin-bottom: 8px;
  font-size: 20px;
  line-height: 1.35;
}

.hero-note p {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: rgba(239, 247, 241, 0.76);
}

.auth-card {
  align-self: center;
  padding: 38px 34px 32px;
  border-radius: 28px;
  background: var(--paper-strong);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 18px 60px rgba(33, 68, 51, 0.1);
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
  box-shadow: 0 0 0 1px rgba(57, 86, 67, 0.12) inset;
}

.auth-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(47, 122, 89, 0.34) inset;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(47, 122, 89, 0.72) inset;
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
  box-shadow: 0 14px 30px rgba(47, 122, 89, 0.22);
}

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0 14px;
  color: #74907e;
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
  border: 1px solid rgba(47, 122, 89, 0.18);
  background: var(--accent-soft);
  color: var(--accent-dark);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.switch-link:hover {
  background: rgba(47, 122, 89, 0.16);
  transform: translateY(-1px);
}

@media (max-width: 1080px) {
  .auth-stage {
    grid-template-columns: 1fr;
  }

  .auth-hero {
    min-height: 500px;
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

  .hero-grid {
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
