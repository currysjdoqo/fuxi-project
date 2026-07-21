<template>
  <Layout :username="username" :avatar="avatar" @show-profile="showProfileModal = true" @logout="handleLogout">
    <div class="settings-page">
        <header class="page-header">
          <div class="header-main">
            <div class="header-nav">
              <div class="header-chip">账户设置</div>
            </div>
            <h1>设置中心</h1>
            <p>统一管理 DeepSeek 调用方式、会员购买、余额兑换、邀请返佣和数据安全配置。</p>
          </div>
          <div class="header-summary">
            <div class="summary-card">
              <span>免费次数</span>
              <strong>{{ settings.free_calls_remaining_today ?? 0 }}/{{ settings.free_daily_limit ?? 5 }}</strong>
            </div>
            <div class="summary-card">
              <span>会员剩余</span>
              <strong>{{ settings.member_calls_remaining ?? 0 }}</strong>
            </div>
            <div class="summary-card">
              <span>余额</span>
              <strong>{{ formatYuan(settings.balance_cents) }}</strong>
            </div>
          </div>
        </header>

        <main class="settings-content">
          <section class="hero-card">
            <div>
              <h2>账户权益概览</h2>
              <p>免费用户每日可调用 5 次，会员套餐按周期发放调用额度，余额可兑换次卡继续使用。</p>
            </div>
            <div class="hero-grid">
              <div class="hero-metric">
                <span>会员状态</span>
                <strong>{{ settings.member_active ? '有效' : '未开通' }}</strong>
                <small>{{ settings.member_expires_at ? `到期时间：${formatDateTime(settings.member_expires_at)}` : '当前未开通会员' }}</small>
              </div>
              <div class="hero-metric">
                <span>次卡余额</span>
                <strong>{{ settings.call_credits ?? 0 }} 次</strong>
                <small>1 元余额可兑换 5 次调用</small>
              </div>
              <div class="hero-metric">
                <span>邀请码</span>
                <strong>{{ settings.invite_code || '未生成' }}</strong>
                <small>邀请好友消费后可持续获得返佣</small>
              </div>
            </div>
          </section>

          <section class="settings-grid">
            <article class="settings-card">
              <div class="section-head">
                <div>
                  <h2>DeepSeek 接口设置</h2>
                  <p>平台仅保留一个统一的个人 DeepSeek API Key。您也可以单独保存自己的个人 Key，用于独立调用。</p>
                </div>
                <el-tag :type="settings.has_custom_ai_api_key ? 'success' : 'info'">
                  {{ settings.has_custom_ai_api_key ? '已保存个人 Key' : '未保存个人 Key' }}
                </el-tag>
              </div>
              <div class="form-block">
                <el-input
                  v-model="apiKey"
                  type="password"
                  show-password
                  placeholder="请输入您的 DeepSeek API Key"
                  autocomplete="off"
                />
                <div class="inline-actions">
                  <el-button type="primary" :loading="savingApiKey" @click="saveApiKey">保存个人 Key</el-button>
                  <el-button :disabled="!settings.has_custom_ai_api_key" :loading="deletingApiKey" @click="removeApiKey">删除个人 Key</el-button>
                </div>
              </div>
            </article>

            <article class="settings-card">
              <div class="section-head">
                <div>
                  <h2>会员购买</h2>
                  <p>会员与次卡并行生效。会员周期内优先消耗会员次数，当前单周期含 80 次调用额度。</p>
                </div>
                <el-tag :type="providerConfigured(membershipProvider) ? 'success' : 'warning'">
                  {{ providerConfigured(membershipProvider) ? '支付方式可用' : '支付方式未配置' }}
                </el-tag>
              </div>

              <div class="plan-grid">
                <button
                  v-for="plan in membershipPlans"
                  :key="plan.value"
                  type="button"
                  class="plan-card"
                  :class="{ active: membershipPlan === plan.value }"
                  @click="membershipPlan = plan.value"
                >
                  <span>{{ plan.label }}</span>
                  <strong>{{ plan.price }}</strong>
                  <small>{{ plan.desc }}</small>
                </button>
              </div>

              <div class="provider-grid">
                <button
                  v-for="provider in paymentProviders"
                  :key="provider.value"
                  type="button"
                  class="provider-card"
                  :class="{ active: membershipProvider === provider.value, disabled: !providerConfigured(provider.value) }"
                  @click="membershipProvider = provider.value"
                  :disabled="!providerConfigured(provider.value)"
                >
                  <span>{{ provider.label }}</span>
                  <small>{{ providerConfigured(provider.value) ? '可用于下单' : '暂未配置' }}</small>
                </button>
              </div>

              <div class="inline-actions">
                <el-button
                  type="primary"
                  :loading="membershipPaying"
                  :disabled="!providerConfigured(membershipProvider)"
                  @click="purchaseMembership"
                >
                  立即开通会员
                </el-button>
              </div>
            </article>

            <article class="settings-card">
              <div class="section-head">
                <div>
                  <h2>余额充值与次卡兑换</h2>
                  <p>余额用于兑换调用次数。每 1 元余额可兑换 5 次调用，兑换后立即到账。</p>
                </div>
                <el-tag type="info">当前余额：{{ formatYuan(settings.balance_cents) }}</el-tag>
              </div>

              <div class="provider-grid">
                <button
                  v-for="provider in paymentProviders"
                  :key="`topup-${provider.value}`"
                  type="button"
                  class="provider-card"
                  :class="{ active: topupProvider === provider.value, disabled: !providerConfigured(provider.value) }"
                  @click="topupProvider = provider.value"
                  :disabled="!providerConfigured(provider.value)"
                >
                  <span>{{ provider.label }}</span>
                  <small>{{ providerConfigured(provider.value) ? '可用于充值' : '暂未配置' }}</small>
                </button>
              </div>

              <div class="topup-row">
                <el-input-number
                  v-model="topupAmountYuan"
                  :min="1"
                  :step="1"
                  :precision="0"
                  controls-position="right"
                />
                <span class="topup-hint">充值 {{ topupAmountYuan }} 元，后续可兑换 {{ topupAmountYuan * 5 }} 次调用</span>
              </div>

              <div class="topup-row exchange-row">
                <el-input-number
                  v-model="exchangeAmountYuan"
                  :min="1"
                  :step="1"
                  :precision="0"
                  controls-position="right"
                />
                <span class="topup-hint">兑换后到账 {{ exchangeAmountYuan * 5 }} 次调用</span>
              </div>

              <div class="inline-actions">
                <el-button
                  type="primary"
                  :loading="topupPaying"
                  :disabled="!providerConfigured(topupProvider)"
                  @click="createTopupOrder"
                >
                  发起余额充值
                </el-button>
                <el-button :loading="exchangingCredits" @click="handleExchangeCredits">兑换次卡</el-button>
              </div>
            </article>

            <article class="settings-card">
              <div class="section-head">
                <div>
                  <h2>邀请返佣</h2>
                  <p>好友使用您的邀请码注册并完成消费后，系统将持续按消费金额返佣到您的余额中，当前返佣比例为 12%。</p>
                </div>
                <el-button text @click="copyInviteCode">复制邀请码</el-button>
              </div>
              <div class="invite-box">
                <span>我的邀请码</span>
                <strong>{{ settings.invite_code || '未生成' }}</strong>
              </div>
              <div class="info-list">
                <div>返佣到账形式：账户余额</div>
                <div>余额用途：可兑换调用次数</div>
                <div>兑换规则：1 元余额 = 5 次调用</div>
              </div>
            </article>

            <article class="settings-card">
              <div class="section-head">
                <div>
                  <h2>支付状态</h2>
                  <p>这里展示当前订单和第三方支付接入状态，便于继续支付或手动刷新回调结果。</p>
                </div>
                <div class="provider-status-list">
                  <el-tag :type="providerConfigured('alipay') ? 'success' : 'warning'">支付宝：{{ providerConfigured('alipay') ? '已配置' : '未配置' }}</el-tag>
                  <el-tag :type="providerConfigured('wechat') ? 'success' : 'warning'">微信支付：{{ providerConfigured('wechat') ? '已配置' : '未配置' }}</el-tag>
                </div>
              </div>

              <div v-if="currentPayment" class="payment-status-card">
                <div class="payment-status-head">
                  <div>
                    <h3>当前订单</h3>
                    <p>订单号：{{ currentPayment.order_no }}</p>
                  </div>
                  <el-tag :type="paymentStatusTagType">{{ paymentStatusText }}</el-tag>
                </div>
                <div class="payment-meta">
                  <div>支付渠道：{{ providerLabel(currentPayment.provider) }}</div>
                  <div>订单类型：{{ productTypeLabel(currentPayment) }}</div>
                  <div>支付金额：{{ formatYuan(currentPayment.amount_cents) }}</div>
                  <div>创建时间：{{ formatDateTime(currentPayment.created_at) }}</div>
                  <div>支付时间：{{ formatDateTime(currentPayment.paid_at) }}</div>
                </div>
                <div class="inline-actions">
                  <el-button
                    v-if="currentPayment.provider === 'alipay' && currentPayment.status === 'pending'"
                    type="primary"
                    @click="continuePayment"
                  >
                    继续支付
                  </el-button>
                  <el-button
                    v-if="currentPayment.provider === 'wechat' && currentPayment.status === 'pending'"
                    type="primary"
                    @click="paymentDialogVisible = true"
                  >
                    查看微信扫码
                  </el-button>
                  <el-button :loading="refreshingPayment" @click="refreshCurrentPayment">刷新订单状态</el-button>
                </div>
              </div>
              <el-empty v-else description="当前暂无待跟进的支付订单" />
            </article>

            <article class="settings-card">
              <div class="section-head">
                <div>
                  <h2>错题移除阈值</h2>
                  <p>答对同一错题达到指定次数后，系统才会将其自动移出错题本。</p>
                </div>
              </div>
              <div class="threshold-row">
                <el-input-number
                  v-model="wrongThreshold"
                  :min="1"
                  :max="10"
                  controls-position="right"
                />
                <el-button type="primary" :loading="savingThreshold" @click="saveThreshold">保存阈值</el-button>
              </div>
            </article>

            <article class="settings-card danger">
              <div class="section-head">
                <div>
                  <h2>清空全部学习数据</h2>
                  <p>将删除题库、练习记录、错题本等内容，该操作不可撤销，请谨慎处理。</p>
                </div>
              </div>
              <div class="inline-actions">
                <el-button type="danger" :loading="clearingData" @click="clearData">清空全部数据</el-button>
              </div>
            </article>
          </section>
        </main>

        <ProfileModal
        v-model:visible="showProfileModal"
        :username="username"
      />

      <el-dialog v-model="paymentDialogVisible" title="微信扫码支付" width="360px" destroy-on-close>
        <div class="wechat-dialog">
          <img v-if="wechatQrImageUrl" :src="wechatQrImageUrl" alt="微信支付二维码" class="wechat-qr" />
          <el-empty v-else description="当前没有可展示的微信支付二维码" />
          <p>请使用微信扫描二维码完成支付，支付完成后可返回本页刷新订单状态。</p>
          <p v-if="currentPayment?.order_no">订单号：{{ currentPayment.order_no }}</p>
        </div>
      </el-dialog>
      </div>
</Layout>
</template>

<script setup>
import { computed, h, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElInput, ElMessage, ElMessageBox } from 'element-plus'
import {
  Close,
  Delete,
  Document,
  List,
  Menu,
  Plus,
  Refresh,
  Setting,
  UserFilled
} from '@element-plus/icons-vue'
import {
  clearAllData,
  createPaymentOrder,
  deleteCustomAiKey,
  exchangeCredits,
  getBillingStatus,
  getPaymentOrder,
  getSettings,
  saveCustomAiKey,
  saveWrongThreshold
} from '../api'
import ProfileModal from '../components/ProfileModal.vue'
import Layout from '../components/Layout/Layout.vue'
import { useUser } from '../composables/useUser'
import { clearAuthSession } from '../utils/authStorage'

const router = useRouter()
const route = useRoute()
const { username, avatar, loadUserInfo } = useUser()

const paymentProviders = [
  { value: 'alipay', label: '支付宝' },
  { value: 'wechat', label: '微信支付' }
]

const membershipPlans = [
  { value: 'month', label: '月度会员', price: '¥12', desc: '30 天有效，含 80 次调用' },
  { value: 'quarter', label: '季度会员', price: '¥30', desc: '90 天有效，含 240 次调用' },
  { value: 'year', label: '年度会员', price: '¥100', desc: '365 天有效，含 960 次调用' }
]

const showProfileModal = ref(false)
const settings = ref({})
const apiKey = ref('')
const wrongThreshold = ref(1)
const membershipPlan = ref('month')
const membershipProvider = ref('alipay')
const topupProvider = ref('alipay')
const topupAmountYuan = ref(12)
const exchangeAmountYuan = ref(1)
const currentPayment = ref(null)
const pendingOrderNo = ref('')
const paymentDialogVisible = ref(false)
const pollingTimer = ref(null)

const savingApiKey = ref(false)
const deletingApiKey = ref(false)
const savingThreshold = ref(false)
const membershipPaying = ref(false)
const topupPaying = ref(false)
const exchangingCredits = ref(false)
const clearingData = ref(false)
const refreshingPayment = ref(false)

const paymentStatusText = computed(() => {
  if (!currentPayment.value) return '无订单'
  if (currentPayment.value.status === 'paid') return '支付成功'
  if (currentPayment.value.status === 'failed') return '支付失败'
  return '等待支付'
})

const paymentStatusTagType = computed(() => {
  if (!currentPayment.value) return 'info'
  if (currentPayment.value.status === 'paid') return 'success'
  if (currentPayment.value.status === 'failed') return 'danger'
  return 'warning'
})

const wechatQrImageUrl = computed(() => {
  const url = currentPayment.value?.provider === 'wechat' ? currentPayment.value?.payment_url : ''
  if (!url) return ''
  return `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(url)}`
})

const goToPath = (path) => {
  if (route.path !== path) {
    router.push(path)
  }
}

const handleLogout = () => {
  clearAuthSession()
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const providerConfigured = (provider) => {
  return Boolean(settings.value?.providers?.[provider]?.configured)
}

const providerLabel = (provider) => {
  if (provider === 'wechat') return '微信支付'
  if (provider === 'alipay') return '支付宝'
  return provider || '-'
}

const productTypeLabel = (order) => {
  if (!order) return '-'
  if (order.product_type === 'membership') {
    const matched = membershipPlans.find((item) => item.value === order.plan)
    return matched ? matched.label : '会员订单'
  }
  if (order.product_type === 'balance_topup') {
    return '余额充值'
  }
  return order.product_type || '-'
}

const formatYuan = (amountCents) => {
  const cents = Number(amountCents || 0)
  return `¥${(cents / 100).toFixed(2)}`
}

const formatDateTime = (value) => {
  if (!value) return '暂无'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '暂无'
  return date.toLocaleString('zh-CN', { hour12: false })
}

const loadSettings = async () => {
  const [settingsData, billingData] = await Promise.all([getSettings(), getBillingStatus()])
  settings.value = {
    ...settingsData,
    providers: billingData?.providers || {}
  }
  wrongThreshold.value = settings.value?.wrong_question_remove_threshold || 1
}

const stopPaymentPolling = () => {
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

const syncPaymentResult = async (orderNo, silent = false) => {
  if (!orderNo) return null
  const order = await getPaymentOrder(orderNo)
  currentPayment.value = order
  pendingOrderNo.value = order.status === 'pending' ? order.order_no : ''
  if (order.status === 'paid') {
    stopPaymentPolling()
    paymentDialogVisible.value = false
    await loadSettings()
    if (!silent) {
      ElMessage.success('支付成功，账户权益已更新')
    }
  } else if (order.status === 'failed') {
    stopPaymentPolling()
    if (!silent) {
      ElMessage.error('订单支付失败，请重新发起支付')
    }
  }
  return order
}

const startPaymentPolling = (orderNo) => {
  if (!orderNo) return
  stopPaymentPolling()
  pendingOrderNo.value = orderNo
  pollingTimer.value = window.setInterval(async () => {
    try {
      await syncPaymentResult(orderNo, true)
    } catch {
      // Ignore polling jitter and allow manual refresh.
    }
  }, 3000)
}

const openPaymentFlow = (order) => {
  currentPayment.value = order
  pendingOrderNo.value = order.order_no
  if (order.provider === 'alipay' && order.payment_url) {
    window.open(order.payment_url, '_blank', 'noopener')
  }
  if (order.provider === 'wechat') {
    paymentDialogVisible.value = true
  }
  startPaymentPolling(order.order_no)
}

const saveApiKey = async () => {
  if (!apiKey.value.trim()) {
    ElMessage.warning('请输入有效的 DeepSeek API Key')
    return
  }
  savingApiKey.value = true
  try {
    await saveCustomAiKey(apiKey.value.trim())
    apiKey.value = ''
    await loadSettings()
    ElMessage.success('个人 DeepSeek API Key 已保存')
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    savingApiKey.value = false
  }
}

const removeApiKey = async () => {
  deletingApiKey.value = true
  try {
    await deleteCustomAiKey()
    await loadSettings()
    ElMessage.success('个人 DeepSeek API Key 已删除')
  } catch (error) {
    ElMessage.error(`删除失败：${error.response?.data?.detail || error.message}`)
  } finally {
    deletingApiKey.value = false
  }
}

const saveThreshold = async () => {
  savingThreshold.value = true
  try {
    await saveWrongThreshold(wrongThreshold.value)
    await loadSettings()
    ElMessage.success('错题移除阈值已保存')
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    savingThreshold.value = false
  }
}

const purchaseMembership = async () => {
  membershipPaying.value = true
  try {
    const order = await createPaymentOrder({
      provider: membershipProvider.value,
      product_type: 'membership',
      plan: membershipPlan.value
    })
    openPaymentFlow(order)
    ElMessage.success('会员订单已创建，请继续完成支付')
  } catch (error) {
    ElMessage.error(`创建订单失败：${error.response?.data?.detail || error.message}`)
  } finally {
    membershipPaying.value = false
  }
}

const createTopupOrder = async () => {
  if (topupAmountYuan.value < 1) {
    ElMessage.warning('充值金额至少为 1 元')
    return
  }
  topupPaying.value = true
  try {
    const order = await createPaymentOrder({
      provider: topupProvider.value,
      product_type: 'balance_topup',
      amount_cents: Number(topupAmountYuan.value) * 100
    })
    openPaymentFlow(order)
    ElMessage.success('充值订单已创建，请继续完成支付')
  } catch (error) {
    ElMessage.error(`创建订单失败：${error.response?.data?.detail || error.message}`)
  } finally {
    topupPaying.value = false
  }
}

const handleExchangeCredits = async () => {
  if (exchangeAmountYuan.value < 1) {
    ElMessage.warning('兑换金额至少为 1 元')
    return
  }
  exchangingCredits.value = true
  try {
    const result = await exchangeCredits(Number(exchangeAmountYuan.value) * 100)
    await loadSettings()
    ElMessage.success(`兑换成功，已到账 ${result.added_credits} 次调用`)
  } catch (error) {
    ElMessage.error(`兑换失败：${error.response?.data?.detail || error.message}`)
  } finally {
    exchangingCredits.value = false
  }
}

const refreshCurrentPayment = async () => {
  if (!currentPayment.value?.order_no) {
    ElMessage.warning('当前没有可刷新的订单')
    return
  }
  refreshingPayment.value = true
  try {
    await syncPaymentResult(currentPayment.value.order_no)
    if (currentPayment.value?.status === 'pending') {
      ElMessage.info('订单仍在等待支付')
    }
  } catch (error) {
    ElMessage.error(`刷新失败：${error.response?.data?.detail || error.message}`)
  } finally {
    refreshingPayment.value = false
  }
}

const continuePayment = () => {
  if (currentPayment.value?.payment_url) {
    window.open(currentPayment.value.payment_url, '_blank', 'noopener')
  }
}

const copyInviteCode = async () => {
  if (!settings.value?.invite_code) {
    ElMessage.warning('当前没有可复制的邀请码')
    return
  }
  try {
    await navigator.clipboard.writeText(settings.value.invite_code)
    ElMessage.success('邀请码已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

const promptPasswordConfirm = async () => {
  const password = ref('')
  await ElMessageBox({
    title: '确认清空数据',
    message: h('div', { class: 'danger-confirm' }, [
      h('p', { class: 'danger-confirm__text' }, '请输入当前登录密码以确认清空全部学习数据。'),
      h(ElInput, {
        modelValue: password.value,
        'onUpdate:modelValue': (value) => {
          password.value = value
        },
        type: 'password',
        showPassword: true,
        placeholder: '请输入当前密码',
        autocomplete: 'current-password'
      })
    ]),
    showCancelButton: true,
    confirmButtonText: '确认清空',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger',
    beforeClose: (action, instance, done) => {
      if (action !== 'confirm') {
        done()
        return
      }
      if (!password.value.trim()) {
        ElMessage.warning('请输入当前密码')
        return
      }
      done()
    }
  })
  return password.value.trim()
}

const clearData = async () => {
  try {
    const password = await promptPasswordConfirm()
    clearingData.value = true
    await clearAllData(password)
    await loadSettings()
    ElMessage.success('全部学习数据已清空')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`清空失败：${error.response?.data?.detail || error.message}`)
    }
  } finally {
    clearingData.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([loadSettings(), loadUserInfo()])
    const orderNo = route.query.order_no || route.query.payment_order || ''
    if (orderNo) {
      await syncPaymentResult(String(orderNo), true)
      if (currentPayment.value?.status === 'pending') {
        startPaymentPolling(String(orderNo))
      }
    }
  } catch (error) {
    ElMessage.error(`加载设置失败：${error.response?.data?.detail || error.message}`)
  }
})

onBeforeUnmount(() => {
  stopPaymentPolling()
})
</script>

<style scoped>
.app-layout {
  --sidebar-width: clamp(220px, 18vw, 256px);
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(184, 92, 56, 0.16), transparent 28%),
    linear-gradient(135deg, #f7f1e7 0%, #f3ece1 52%, #ebe0d3 100%);
}

.mobile-nav-mask {
  position: fixed;
  inset: 0;
  background: rgba(24, 18, 12, 0.45);
  z-index: 90;
}

.sidebar {
  width: var(--sidebar-width);
  background: linear-gradient(180deg, #3d2f24 0%, #2b2219 100%);
  color: #f8f4ec;
  display: flex;
  flex-direction: column;
  position: relative;
  flex: 0 0 var(--sidebar-width);
  min-height: 100vh;
  z-index: 100;
  transition: width 0.24s ease, transform 0.24s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 84px;
  flex-basis: 84px;
}

.sidebar.collapsed .logo-copy,
.sidebar.collapsed .nav-section-title,
.sidebar.collapsed .nav-item span,
.sidebar.collapsed .user-details {
  opacity: 0;
  pointer-events: none;
}

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.logo-icon {
  font-size: 30px;
  color: #d99873;
  flex-shrink: 0;
}

.logo-copy h2 {
  margin: 0;
  font-size: 18px;
  color: #fffaf1;
}

.logo-copy span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.64);
}

.nav-menu {
  flex: 1;
  padding: 18px 12px;
  overflow-y: auto;
}

.nav-section-title {
  margin: 0 8px 10px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.45);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  color: #ccbfae;
  transition: all 0.2s ease;
  margin-bottom: 6px;
}

.nav-item:hover {
  background: rgba(217, 152, 115, 0.12);
  color: #fff9f1;
}

.nav-item.active {
  background: linear-gradient(135deg, #b85c38 0%, #8e4528 100%);
  color: #fff;
  box-shadow: 0 10px 24px rgba(142, 69, 40, 0.24);
}

.nav-item .el-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.user-section {
  padding: 16px 18px 22px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.username {
  font-size: 14px;
  color: #fffaf1;
}

.logout-btn {
  font-size: 12px;
  color: #c9b8a4;
  cursor: pointer;
}

.logout-btn:hover {
  color: #fffaf1;
}

.main-content {
  flex: 1;
  min-width: 0;
  min-height: 100vh;
  position: relative;
}

.desktop-sidebar-handle {
  position: absolute;
  top: 20px;
  left: 12px;
  z-index: 20;
  width: 28px;
  height: 56px;
  border: none;
  border-radius: 14px;
  background: rgba(61, 47, 36, 0.9);
  color: #fff;
  cursor: pointer;
}

.desktop-sidebar-handle.collapsed {
  left: 10px;
}

.settings-page {
  min-height: 100vh;
  padding: 22px 26px 32px 48px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.header-chip {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(184, 92, 56, 0.12);
  color: #914b2d;
  font-size: 12px;
  font-weight: 600;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 30px;
  color: #2f241b;
}

.page-header p {
  margin: 0;
  max-width: 720px;
  color: #736153;
  line-height: 1.65;
}

.header-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: 12px;
  width: min(440px, 100%);
}

.summary-card,
.hero-metric,
.settings-card,
.hero-card {
  background: rgba(255, 252, 247, 0.92);
  border: 1px solid rgba(125, 86, 63, 0.12);
  box-shadow: 0 16px 32px rgba(96, 70, 50, 0.08);
}

.summary-card {
  border-radius: 16px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-card span,
.hero-metric span {
  font-size: 12px;
  color: #8b725d;
}

.summary-card strong,
.hero-metric strong {
  font-size: 20px;
  color: #2f241b;
}

.settings-content {
  display: grid;
  gap: 18px;
}

.hero-card {
  border-radius: 24px;
  padding: 24px;
  display: grid;
  gap: 18px;
}

.hero-card h2,
.settings-card h2 {
  margin: 0 0 8px;
  color: #2f241b;
}

.hero-card p,
.settings-card p {
  margin: 0;
  color: #746151;
  line-height: 1.65;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.hero-metric {
  border-radius: 18px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero-metric small {
  color: #8f7964;
  line-height: 1.5;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.settings-card {
  border-radius: 20px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.settings-card.danger {
  border-color: rgba(196, 64, 64, 0.18);
  background: rgba(255, 249, 249, 0.96);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.form-block,
.inline-actions,
.threshold-row,
.topup-row,
.provider-grid,
.plan-grid {
  display: flex;
  gap: 12px;
}

.form-block {
  flex-direction: column;
}

.inline-actions {
  flex-wrap: wrap;
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.plan-card,
.provider-card {
  border: 1px solid rgba(143, 103, 78, 0.18);
  background: #fffdfa;
  border-radius: 16px;
  padding: 16px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.plan-card:hover,
.provider-card:hover {
  transform: translateY(-1px);
  border-color: rgba(184, 92, 56, 0.42);
}

.plan-card.active,
.provider-card.active {
  border-color: #b85c38;
  background: linear-gradient(135deg, rgba(184, 92, 56, 0.1), rgba(255, 249, 244, 1));
  box-shadow: 0 10px 24px rgba(184, 92, 56, 0.12);
}

.provider-card.disabled {
  opacity: 0.56;
  cursor: not-allowed;
}

.plan-card span,
.provider-card span {
  color: #5f4a3a;
  font-weight: 600;
}

.plan-card strong {
  font-size: 22px;
  color: #2f241b;
}

.plan-card small,
.provider-card small,
.topup-hint {
  color: #8b725d;
  line-height: 1.5;
}

.topup-row,
.threshold-row {
  align-items: center;
  flex-wrap: wrap;
}

.exchange-row {
  margin-top: -6px;
}

.invite-box {
  border-radius: 18px;
  padding: 18px;
  background: linear-gradient(135deg, #fff7ef 0%, #fffdf8 100%);
  border: 1px dashed rgba(184, 92, 56, 0.34);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.invite-box strong {
  font-size: 26px;
  letter-spacing: 0.08em;
  color: #8e4528;
}

.info-list {
  display: grid;
  gap: 8px;
  color: #6f5b4b;
}

.provider-status-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.payment-status-card {
  border-radius: 18px;
  border: 1px solid rgba(143, 103, 78, 0.14);
  background: #fffdfa;
  padding: 18px;
  display: grid;
  gap: 14px;
}

.payment-status-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.payment-status-head h3 {
  margin: 0 0 6px;
  color: #2f241b;
}

.payment-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
  color: #6f5b4b;
}

.wechat-dialog {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  color: #5f4a3a;
}

.wechat-qr {
  width: 240px;
  height: 240px;
  border-radius: 16px;
  border: 1px solid rgba(143, 103, 78, 0.14);
  background: #fff;
  padding: 10px;
}

:deep(.danger-confirm__text) {
  margin: 0 0 12px;
  color: #5f4a3a;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner),
:deep(.el-input-number) {
  border-radius: 12px;
}

@media (max-width: 1180px) {
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    transform: translateX(-100%);
    width: min(280px, 78vw);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .settings-page {
    padding: 18px 16px 28px;
  }

  .desktop-sidebar-handle {
    display: none;
  }

  .page-header,
  .section-head {
    flex-direction: column;
  }

  .header-summary,
  .hero-grid,
  .settings-grid,
  .plan-grid,
  .provider-grid,
  .payment-meta {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .settings-card,
  .hero-card {
    padding: 18px;
  }

  .page-header h1 {
    font-size: 24px;
  }

  .invite-box strong {
    font-size: 22px;
  }
}
</style>
