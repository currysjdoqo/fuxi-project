<template>
  <div class="auth-page">
    <div class="auth-shell">
      <aside class="auth-aside">
        <p class="aside-tag">Learning Console</p>
        <h1>欢迎回来</h1>
        <p class="aside-desc">请先登录账号，再进入练习与题库管理页面。</p>
      </aside>

      <section class="auth-card">
        <header class="card-header">
          <h2>账号登录</h2>
          <p>输入用户名和密码</p>
        </header>

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
              {{ loading ? '登录中...' : '登录' }}
            </el-button>
          </el-form-item>
        </el-form>

        <footer class="card-footer">
          <span>还没有账号？</span>
          <el-button type="primary" link @click="router.push('/auth/register')">去注册</el-button>
        </footer>
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
    localStorage.setItem('auth_token', result.token)
    localStorage.setItem('auth_username', result.username)
    sessionStorage.setItem('auth_session_ok', '1')
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
.auth-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at 10% 15%, rgba(217, 119, 6, 0.18), transparent 42%),
    radial-gradient(circle at 90% 85%, rgba(15, 23, 42, 0.16), transparent 44%),
    linear-gradient(130deg, #f7f3ea 0%, #e9eef4 56%, #f8f8f6 100%);
}

.auth-shell {
  min-height: calc(100vh - 48px);
  max-width: 980px;
  margin: 0 auto;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.08);
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: rgba(255, 255, 255, 0.8);
}

.auth-aside {
  padding: 56px 44px;
  color: #10213d;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.9) 0%, rgba(242, 247, 252, 0.74) 100%),
    repeating-linear-gradient(
      -45deg,
      rgba(148, 163, 184, 0.08) 0,
      rgba(148, 163, 184, 0.08) 7px,
      transparent 7px,
      transparent 22px
    );
}

.aside-tag {
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  color: #b45309;
  margin-bottom: 14px;
}

.auth-aside h1 {
  margin: 0 0 12px;
  font-size: 38px;
  line-height: 1.1;
}

.aside-desc {
  margin: 0;
  color: #334155;
  font-size: 15px;
  line-height: 1.7;
}

.auth-card {
  padding: 56px 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: rgba(255, 255, 255, 0.96);
}

.card-header {
  margin-bottom: 24px;
}

.card-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #0f172a;
}

.card-header p {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.auth-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 0 0 1px #d4dbe6 inset;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #0f172a inset;
}

.submit-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  border: none;
  font-size: 15px;
  font-weight: 700;
  background: linear-gradient(90deg, #0f172a 0%, #1d4ed8 100%);
}

.card-footer {
  margin-top: 6px;
  text-align: center;
  font-size: 14px;
  color: #64748b;
}

@media (max-width: 900px) {
  .auth-page {
    padding: 12px;
  }

  .auth-shell {
    min-height: calc(100vh - 24px);
    grid-template-columns: 1fr;
  }

  .auth-aside {
    padding: 32px 22px 26px;
  }

  .auth-aside h1 {
    font-size: 32px;
  }

  .auth-card {
    padding: 28px 22px 24px;
  }
}
</style>
