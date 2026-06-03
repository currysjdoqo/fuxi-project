<template>
  <div class="auth-page">
    <div class="auth-shell">
      <aside class="auth-aside">
        <p class="aside-tag">Create account</p>
        <h1>注册新账号</h1>
        <p class="aside-desc">先完成注册，再使用账号密码登录进入主页。</p>
      </aside>

      <section class="auth-card">
        <header class="card-header">
          <h2>账号注册</h2>
          <p>创建用户名和密码</p>
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
              placeholder="密码（至少 6 位）"
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
              {{ loading ? '注册中...' : '创建账号' }}
            </el-button>
          </el-form-item>
        </el-form>

        <footer class="card-footer">
          <span>已有账号？</span>
          <el-button type="primary" link @click="router.push('/auth/login')">去登录</el-button>
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
.auth-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at 12% 20%, rgba(5, 150, 105, 0.16), transparent 38%),
    radial-gradient(circle at 88% 80%, rgba(15, 23, 42, 0.16), transparent 42%),
    linear-gradient(130deg, #f3f8f5 0%, #edf2f7 56%, #f8f7f2 100%);
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
  color: #0f172a;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.9) 0%, rgba(241, 245, 249, 0.72) 100%),
    repeating-linear-gradient(
      45deg,
      rgba(16, 185, 129, 0.08) 0,
      rgba(16, 185, 129, 0.08) 7px,
      transparent 7px,
      transparent 22px
    );
}

.aside-tag {
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  color: #047857;
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
  box-shadow: 0 0 0 2px #0f766e inset;
}

.submit-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  border: none;
  font-size: 15px;
  font-weight: 700;
  background: linear-gradient(90deg, #0f766e 0%, #16a34a 100%);
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
