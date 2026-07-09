<template>
  <div class="app-layout friends-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>

    <nav class="sidebar app-sidebar-root">
      <div class="app-sidebar-logo">
        <el-icon class="app-sidebar-logo-icon"><Document /></el-icon>
        <div class="app-sidebar-logo-copy">
          <h2>题库管理系统</h2>
          <span>Practice Workspace</span>
        </div>
        <el-button
          v-if="isMobileNav"
          circle
          text
          class="app-sidebar-mobile-close"
          :icon="CloseBold"
          @click="closeMobileNav"
        />
      </div>

      <div class="app-sidebar-nav">
        <div class="app-sidebar-section-title">功能导航</div>
        <div
          v-for="item in navItems"
          :key="item.path"
          class="app-sidebar-nav-item"
          :class="{ active: route.path === item.path }"
          @click="goToPath(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>

      <div class="app-sidebar-user">
        <div class="app-sidebar-user-info">
          <div
            class="app-sidebar-avatar"
            :style="{ background: avatar ? `url(${avatar}) center/cover` : undefined }"
            @click="showProfileModal = true"
          >
            <template v-if="!avatar">{{ username.charAt(0).toUpperCase() }}</template>
          </div>
          <div class="app-sidebar-user-details">
            <span class="app-sidebar-username">{{ username }}</span>
            <span class="app-sidebar-logout" @click="handleLogout">退出登录</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="main-content">
      <button
        v-if="!isMobileNav"
        type="button"
        class="desktop-sidebar-handle"
        :class="{ collapsed: sidebarCollapsed }"
        :aria-label="sidebarCollapsed ? '展开导航栏' : '隐藏导航栏'"
        @click="toggleSidebar"
      >
        {{ sidebarCollapsed ? '>' : '<' }}
      </button>

      <section class="friends-page">
        <header class="page-header">
          <div class="header-main">
            <div class="header-nav">
              <el-button
                v-if="isMobileNav"
                circle
                text
                class="header-nav-btn"
                :icon="Menu"
                @click="toggleMobileNav"
              />
              <span class="header-pill">Real-Time Chat</span>
            </div>
            <h1>好友互动</h1>
            <p>好友搜索、请求处理、即时聊天和习题集分享都集中在这里。</p>
          </div>
          <div class="header-actions">
            <el-button class="focus-action" :icon="Menu" @click="toggleWorkspaceSidebar">
              {{ sidebarCollapsed ? '恢复导航' : '收起导航' }}
            </el-button>
            <el-button type="primary" :icon="Plus" @click="openAddFriendDialog">添加好友</el-button>
            <el-button :icon="Bell" @click="activePane = 'requests'">
              请求
              <el-badge v-if="pendingRequests.length" :value="pendingRequests.length" class="inline-badge" />
            </el-button>
            <el-button :icon="Share" @click="activePane = 'shares'">
              分享收件箱
              <el-badge v-if="pendingShareCount" :value="pendingShareCount" class="inline-badge" />
            </el-button>
          </div>
        </header>

        <div class="friends-board">
          <aside class="friends-sidebar">
            <div class="sidebar-top">
              <div>
                <p class="panel-kicker">Connections</p>
                <h2>好友中心</h2>
              </div>
              <el-button text :icon="RefreshRight" @click="refreshAllData">刷新</el-button>
            </div>

            <div class="summary-grid">
              <article class="summary-card">
                <span>好友</span>
                <strong>{{ friends.length }}</strong>
              </article>
              <article class="summary-card accent">
                <span>未读消息</span>
                <strong>{{ totalUnread }}</strong>
              </article>
              <article class="summary-card warm">
                <span>待处理请求</span>
                <strong>{{ pendingRequests.length }}</strong>
              </article>
            </div>

            <div class="pane-switch">
              <button
                v-for="pane in panes"
                :key="pane.value"
                type="button"
                class="pane-button"
                :class="{ active: activePane === pane.value }"
                @click="activePane = pane.value"
              >
                <span>{{ pane.label }}</span>
                <em v-if="pane.count">{{ pane.count }}</em>
              </button>
            </div>

            <div class="sidebar-scroll">
              <template v-if="activePane === 'friends'">
                <div v-if="friends.length" class="friend-list">
                  <button
                    v-for="friend in friends"
                    :key="friend.user_id"
                    type="button"
                    class="friend-card"
                    :class="{ active: selectedFriend?.user_id === friend.user_id }"
                    @click="selectFriend(friend)"
                  >
                    <el-avatar :size="42" :src="friend.avatar">{{ friendInitial(friend) }}</el-avatar>
                    <div class="friend-meta">
                      <strong>{{ friend.username }}</strong>
                      <span>ID {{ friend.user_code }}</span>
                      <p>{{ friend.signature || '这个好友还没有填写签名。' }}</p>
                    </div>
                    <div class="friend-side">
                      <el-badge v-if="friend.unread_count" :value="friend.unread_count" />
                      <el-button text type="danger" :icon="Delete" @click.stop="handleRemoveFriend(friend)">
                        删除
                      </el-button>
                    </div>
                  </button>
                </div>
                <el-empty v-else description="还没有好友，先通过 10 位 ID 添加一个。" :image-size="90" />
              </template>

              <template v-else-if="activePane === 'requests'">
                <div v-if="pendingRequests.length" class="request-list">
                  <article v-for="request in pendingRequests" :key="request.request_id" class="request-card">
                    <div class="request-head">
                      <el-avatar :size="42" :src="request.avatar">{{ friendInitial(request) }}</el-avatar>
                      <div>
                        <strong>{{ request.username }}</strong>
                        <span>ID {{ request.user_code }}</span>
                      </div>
                    </div>
                    <p>{{ request.signature || '对方还没有填写签名。' }}</p>
                    <div class="request-actions">
                      <el-button size="small" type="success" @click="handleAccept(request.user_id)">同意</el-button>
                      <el-button size="small" type="danger" @click="handleReject(request.user_id)">拒绝</el-button>
                    </div>
                  </article>
                </div>
                <el-empty v-else description="当前没有待处理好友请求。" :image-size="90" />
              </template>

              <template v-else>
                <div v-if="shares.length" class="share-list">
                  <article
                    v-for="share in shares"
                    :key="share.share_id"
                    class="share-card"
                    :class="{ pending: share.accepted === 0 }"
                  >
                    <div class="request-head">
                      <el-avatar :size="42" :src="share.from_user_avatar">{{ friendInitial(share) }}</el-avatar>
                      <div>
                        <strong>{{ share.from_username }}</strong>
                        <span>{{ share.subject_name }} · {{ share.question_count }} 题</span>
                      </div>
                    </div>
                    <p>{{ formatDateTime(share.created_at) }}</p>
                    <div v-if="share.accepted === 0" class="request-actions">
                      <el-button size="small" type="primary" @click="handleAcceptShare(share)">接受</el-button>
                      <el-button size="small" @click="handleRejectShare(share.share_id)">拒绝</el-button>
                    </div>
                    <el-tag v-else type="success" effect="plain">已接受</el-tag>
                  </article>
                </div>
                <el-empty v-else description="还没有收到习题集分享。" :image-size="90" />
              </template>
            </div>
          </aside>

          <section class="chat-stage">
            <template v-if="selectedFriend">
              <div class="chat-header">
                <div class="chat-profile">
                  <el-avatar :size="50" :src="selectedFriend.avatar">{{ friendInitial(selectedFriend) }}</el-avatar>
                  <div>
                    <h3>{{ selectedFriend.username }}</h3>
                    <p>ID {{ selectedFriend.user_code }}<span v-if="selectedFriend.signature"> · {{ selectedFriend.signature }}</span></p>
                  </div>
                </div>
                <div class="chat-header-actions">
                  <el-button :icon="Share" @click="openShareDialog">分享习题集</el-button>
                  <span class="socket-status" :class="socketState">{{ socketStatusText }}</span>
                  <el-tag v-if="selectedFriend.unread_count" type="danger" effect="plain">
                    {{ selectedFriend.unread_count }} 条未读
                  </el-tag>
                </div>
              </div>

              <div ref="messageListRef" class="message-list">
                <div v-if="friendShares.length" class="inline-share-box">
                  <div class="inline-share-title">与 {{ selectedFriend.username }} 相关的习题集分享</div>
                  <article v-for="share in friendShares" :key="`inline-${share.share_id}`" class="inline-share-card">
                    <div>
                      <strong>{{ share.subject_name }}</strong>
                      <span>{{ share.question_count }} 题 · {{ formatDateTime(share.created_at) }}</span>
                    </div>
                    <div v-if="share.accepted === 0" class="request-actions">
                      <el-button size="small" type="primary" @click="handleAcceptShare(share)">接受</el-button>
                      <el-button size="small" @click="handleRejectShare(share.share_id)">拒绝</el-button>
                    </div>
                    <el-tag v-else type="success" effect="plain">已接受</el-tag>
                  </article>
                </div>

                <div v-if="messages.length" class="message-stream">
                  <article
                    v-for="message in messages"
                    :key="message.id"
                    class="message-row"
                    :class="{ self: message.sender_id === currentUserId }"
                  >
                    <el-avatar :size="34" :src="message.sender_id === currentUserId ? avatar : selectedFriend.avatar">
                      {{ message.sender_id === currentUserId ? username.charAt(0).toUpperCase() : friendInitial(selectedFriend) }}
                    </el-avatar>
                    <div class="message-bubble">
                      <div class="message-text">{{ message.content }}</div>
                      <div class="message-meta">
                        <span>{{ formatTime(message.created_at) }}</span>
                        <span v-if="message.sender_id === currentUserId">{{ message.is_read ? '已读' : '未读' }}</span>
                      </div>
                    </div>
                  </article>
                </div>
                <el-empty v-else description="还没有聊天记录，先发一条消息。" :image-size="100" />
              </div>

              <div class="message-composer">
                <el-input
                  v-model="messageInput"
                  type="textarea"
                  :rows="3"
                  resize="none"
                  placeholder="输入消息，按 Ctrl + Enter 发送"
                  @keydown.ctrl.enter.prevent="handleSendMessage"
                />
                <div class="composer-actions">
                  <span>{{ messageInput.trim().length }}/500 · {{ isSocketConnected ? '实时连接已建立' : '实时连接重连中，必要时将回退到 HTTP 发送' }}</span>
                  <el-button type="primary" :disabled="!messageInput.trim()" @click="handleSendMessage">发送</el-button>
                </div>
              </div>
            </template>

            <div v-else class="chat-empty">
              <el-icon><ChatDotRound /></el-icon>
              <h3>选择一个好友开始聊天</h3>
              <p>左侧列表会显示未读消息、好友请求和收到的习题集分享。</p>
            </div>
          </section>
        </div>
      </section>
    </div>

    <el-dialog v-model="showAddFriendDialog" title="通过好友 ID 添加" width="420px">
      <div class="dialog-stack">
        <el-input
          v-model="searchCode"
          maxlength="10"
          placeholder="输入 10 位数字好友 ID"
          @keyup.enter="handleSearchUser"
        >
          <template #append>
            <el-button type="primary" @click="handleSearchUser">搜索</el-button>
          </template>
        </el-input>

        <el-alert
          v-if="searchError"
          type="error"
          :closable="false"
          show-icon
          :title="searchError"
        />

        <article v-if="searchResult" class="search-card">
          <div class="request-head">
            <el-avatar :size="48" :src="searchResult.avatar">{{ friendInitial(searchResult) }}</el-avatar>
            <div>
              <strong>{{ searchResult.username }}</strong>
              <span>ID {{ searchResult.user_code }}</span>
            </div>
          </div>
          <p>{{ searchResult.signature || '对方还没有填写签名。' }}</p>
          <el-tag v-if="searchResult.friend_status === 'accepted'" type="success">已是好友</el-tag>
          <el-tag v-else-if="searchResult.friend_status === 'pending'" type="warning">请求待处理</el-tag>
          <el-button v-else type="primary" @click="handleSendRequest">发送好友请求</el-button>
        </article>
      </div>
    </el-dialog>

    <el-dialog v-model="showShareDialog" title="分享习题集" width="460px">
      <div class="dialog-stack">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          :title="selectedFriend ? `将题集分享给 ${selectedFriend.username}` : '请选择好友后再分享'"
        />
        <el-select v-model="selectedSubjectId" placeholder="选择要分享的习题集" style="width: 100%">
          <el-option
            v-for="subject in subjects"
            :key="subject.id"
            :label="`${subject.name} (${subject.question_count ?? 0} 题)`"
            :value="subject.id"
          />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showShareDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedSubjectId || !selectedFriend" @click="handleShare">
          确认分享
        </el-button>
      </template>
    </el-dialog>

    <ProfileModal v-model:visible="showProfileModal" :username="username" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bell,
  ChatDotRound,
  CloseBold,
  Delete,
  Document,
  List,
  Menu,
  Plus,
  Refresh,
  RefreshRight,
  Setting,
  Share,
  User,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  acceptFriendRequest,
  acceptShare,
  getFriends,
  getMessages,
  getPendingRequests,
  getShareList,
  getSubjects,
  rejectFriendRequest,
  rejectShare,
  removeFriend,
  searchUser,
  sendFriendRequest,
  sendMessage,
  shareSubject,
} from '../api'
import ProfileModal from '../components/ProfileModal.vue'
import { useChatSocket } from '../composables/useChatSocket'
import { useSidebarLayout } from '../composables/useSidebarLayout'
import { useUser } from '../composables/useUser'
import { clearAuthSession, getAuthUserId } from '../utils/authStorage'

const route = useRoute()
const router = useRouter()
const { sidebarCollapsed, mobileNavOpen, isMobileNav, toggleSidebar, toggleMobileNav, closeMobileNav } = useSidebarLayout()
const { username, avatar, loadUserInfo } = useUser()

const navItems = [
  { path: '/', label: '练习模式', icon: Document },
  { path: '/friends', label: '好友互动', icon: User },
  { path: '/plan', label: '学习计划', icon: List },
  { path: '/import', label: '导入习题', icon: Plus },
  { path: '/review', label: '复习模式', icon: Refresh },
  { path: '/settings', label: '设置', icon: Setting },
]

const activePane = ref('friends')
const friends = ref([])
const pendingRequests = ref([])
const shares = ref([])
const selectedFriend = ref(null)
const messages = ref([])
const subjects = ref([])
const selectedSubjectId = ref(null)
const currentUserId = ref(Number(getAuthUserId()) || null)
const messageInput = ref('')
const searchCode = ref('')
const searchResult = ref(null)
const searchError = ref('')
const showAddFriendDialog = ref(false)
const showShareDialog = ref(false)
const showProfileModal = ref(false)
const messageListRef = ref(null)
const previousSidebarState = ref(false)
const panes = computed(() => [
  { value: 'friends', label: '好友', count: friends.value.length || null },
  { value: 'requests', label: '请求', count: pendingRequests.value.length || null },
  { value: 'shares', label: '分享', count: pendingShareCount.value || null },
])

const totalUnread = computed(() => friends.value.reduce((sum, item) => sum + (item.unread_count || 0), 0))
const pendingShareCount = computed(() => shares.value.filter((item) => item.accepted === 0).length)
const friendShares = computed(() => {
  if (!selectedFriend.value) return []
  return shares.value.filter((item) => item.from_user_id === selectedFriend.value.user_id)
})

const sortFriends = () => {
  friends.value = [...friends.value].sort((a, b) => {
    if ((b.unread_count || 0) !== (a.unread_count || 0)) {
      return (b.unread_count || 0) - (a.unread_count || 0)
    }
    return a.username.localeCompare(b.username, 'zh-CN')
  })
}

const mergeSelectedFriend = () => {
  if (!selectedFriend.value) return
  const matched = friends.value.find((item) => item.user_id === selectedFriend.value.user_id)
  if (matched) {
    selectedFriend.value = matched
  } else {
    selectedFriend.value = null
    messages.value = []
  }
}

const setFriendUnread = (friendId, count) => {
  const friend = friends.value.find((item) => item.user_id === friendId)
  if (!friend) return
  friend.unread_count = Math.max(0, count)
  sortFriends()
  mergeSelectedFriend()
}

const bumpFriendUnread = (friendId) => {
  const friend = friends.value.find((item) => item.user_id === friendId)
  if (!friend) return
  friend.unread_count = (friend.unread_count || 0) + 1
  sortFriends()
  mergeSelectedFriend()
}

const upsertMessage = async (message) => {
  const index = messages.value.findIndex((item) => item.id === message.id)
  if (index >= 0) {
    messages.value[index] = { ...messages.value[index], ...message }
  } else {
    messages.value = [...messages.value, message].sort((a, b) => {
      if (a.created_at === b.created_at) return a.id - b.id
      return a.created_at.localeCompare(b.created_at)
    })
  }
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const parseServerDate = (value) => {
  if (!value) return null
  if (value instanceof Date) return value
  if (typeof value !== 'string') {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? null : date
  }

  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

const formatTime = (value) => {
  const date = parseServerDate(value)
  if (!date) return '--:--'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatDateTime = (value) => {
  const date = parseServerDate(value)
  if (!date) return '--'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const friendInitial = (friend) => (friend?.username || friend?.from_username || '?').charAt(0).toUpperCase()

const loadFriendsData = async () => {
  const result = await getFriends()
  friends.value = result.friends || []
  sortFriends()
  mergeSelectedFriend()
}

const loadPendingData = async () => {
  const result = await getPendingRequests()
  pendingRequests.value = result.pending || []
}

const loadShareData = async () => {
  const result = await getShareList()
  shares.value = result.shares || []
}

const loadSubjectsData = async () => {
  const result = await getSubjects()
  subjects.value = Array.isArray(result) ? result : (result.subjects || [])
}

const loadMessagesData = async (friendId, { silent = false } = {}) => {
  if (!friendId) return
  try {
    const result = await getMessages(friendId)
    messages.value = result.messages || []
    setFriendUnread(friendId, 0)
    await nextTick()
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  } catch (error) {
    if (!silent) {
      ElMessage.error(error.response?.data?.detail || '加载聊天记录失败')
    }
  }
}

const refreshAllData = async () => {
  try {
    await Promise.all([loadFriendsData(), loadPendingData(), loadShareData()])
    if (selectedFriend.value) {
      await loadMessagesData(selectedFriend.value.user_id, { silent: true })
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '刷新失败')
  }
}

const socketEventHandlers = {
  async onEvent(payload) {
    if (payload.type === 'message.new') {
      const message = payload.message
      const partnerId = message.sender_id === currentUserId.value ? message.receiver_id : message.sender_id

      if (selectedFriend.value?.user_id === partnerId) {
        await upsertMessage(message)
        if (message.sender_id !== currentUserId.value) {
          setFriendUnread(partnerId, 0)
          if (isSocketConnected.value) {
            openChatSocket(partnerId)
          }
        }
      } else if (message.sender_id !== currentUserId.value) {
        bumpFriendUnread(partnerId)
      }
      return
    }

    if (payload.type === 'message.read') {
      const readSet = new Set(payload.message_ids || [])
      messages.value = messages.value.map((message) => (
        readSet.has(message.id) ? { ...message, is_read: 1 } : message
      ))
      return
    }

    if (payload.type === 'chat.opened') {
      if (selectedFriend.value?.user_id === payload.friend_id) {
        setFriendUnread(payload.friend_id, 0)
      }
      return
    }

    if (payload.type === 'friendship.updated') {
      await Promise.all([loadFriendsData(), loadPendingData()])
      return
    }

    if (payload.type === 'error' && payload.detail) {
      ElMessage.error(payload.detail)
    }
  },
  onOpen() {
    if (selectedFriend.value) {
      openChatSocket(selectedFriend.value.user_id)
    }
  },
}

const { state: socketState, isConnected: isSocketConnected, connect, disconnect, openChat, closeChat, sendMessage: sendSocketMessage } = useChatSocket(socketEventHandlers)

const socketStatusText = computed(() => {
  if (socketState.value === 'connected') return '实时在线'
  if (socketState.value === 'reconnecting') return '重连中'
  if (socketState.value === 'connecting') return '连接中'
  return '离线'
})

const toggleWorkspaceSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const goToPath = (path) => {
  closeMobileNav()
  router.push(path)
}

const handleLogout = () => {
  disconnect()
  clearAuthSession()
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const openChatSocket = (friendId) => {
  if (!friendId || !isSocketConnected.value) return
  openChat(friendId)
  setFriendUnread(friendId, 0)
}

const selectFriend = async (friend) => {
  if (selectedFriend.value?.user_id && selectedFriend.value.user_id !== friend.user_id) {
    closeChat()
  }
  selectedFriend.value = friend
  activePane.value = 'friends'
  await loadMessagesData(friend.user_id)
  openChatSocket(friend.user_id)
}

const openAddFriendDialog = () => {
  showAddFriendDialog.value = true
  searchCode.value = ''
  searchResult.value = null
  searchError.value = ''
}

const handleSearchUser = async () => {
  const code = searchCode.value.trim()
  if (!/^\d{10}$/.test(code)) {
    searchError.value = '请输入 10 位数字好友 ID'
    searchResult.value = null
    return
  }
  searchError.value = ''
  searchResult.value = null
  try {
    searchResult.value = await searchUser(code)
  } catch (error) {
    searchError.value = error.response?.data?.detail || '搜索失败'
  }
}

const handleSendRequest = async () => {
  if (!searchResult.value) return
  try {
    await sendFriendRequest(searchResult.value.user_code)
    ElMessage.success('好友请求已发送')
    showAddFriendDialog.value = false
    await loadPendingData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '发送好友请求失败')
  }
}

const handleAccept = async (friendId) => {
  try {
    await acceptFriendRequest(friendId)
    ElMessage.success('已同意好友请求')
    await Promise.all([loadPendingData(), loadFriendsData()])
    activePane.value = 'friends'
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const handleReject = async (friendId) => {
  try {
    await rejectFriendRequest(friendId)
    ElMessage.success('已拒绝好友请求')
    await loadPendingData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const handleRemoveFriend = async (friend) => {
  try {
    await ElMessageBox.confirm(`确定删除好友“${friend.username}”吗？`, '删除好友', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await removeFriend(friend.user_id)
    ElMessage.success('好友已删除')
    if (selectedFriend.value?.user_id === friend.user_id) {
      closeChat()
      selectedFriend.value = null
      messages.value = []
    }
    await loadFriendsData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除好友失败')
    }
  }
}

const handleSendMessage = async () => {
  const content = messageInput.value.trim()
  if (!content || !selectedFriend.value) return

  messageInput.value = ''
  if (isSocketConnected.value && sendSocketMessage(selectedFriend.value.user_id, content.slice(0, 500))) {
    return
  }

  try {
    await sendMessage(selectedFriend.value.user_id, content.slice(0, 500))
    await loadMessagesData(selectedFriend.value.user_id, { silent: true })
  } catch (error) {
    messageInput.value = content
    ElMessage.error(error.response?.data?.detail || '发送消息失败')
  }
}

const openShareDialog = async () => {
  if (!selectedFriend.value) {
    ElMessage.warning('请先选择好友')
    return
  }
  await loadSubjectsData()
  showShareDialog.value = true
}

const handleShare = async () => {
  if (!selectedFriend.value || !selectedSubjectId.value) return
  try {
    await shareSubject(selectedSubjectId.value, selectedFriend.value.user_id)
    ElMessage.success('分享请求已发送')
    showShareDialog.value = false
    selectedSubjectId.value = null
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '分享失败')
  }
}

const handleAcceptShare = async (share) => {
  try {
    const result = await acceptShare(share.share_id)
    ElMessage.success(`已接收 ${result.question_count ?? 0} 道题`)
    await Promise.all([loadShareData(), loadSubjectsData()])
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '接受分享失败')
  }
}

const handleRejectShare = async (shareId) => {
  try {
    await rejectShare(shareId)
    ElMessage.success('已拒绝分享')
    await loadShareData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '拒绝分享失败')
  }
}

watch(() => selectedFriend.value?.user_id, (friendId, previousFriendId) => {
  if (previousFriendId && previousFriendId !== friendId) {
    closeChat()
  }
  if (friendId && isSocketConnected.value) {
    openChatSocket(friendId)
  }
  if (!friendId) {
    closeChat()
  }
})

watch(isSocketConnected, (connected) => {
  if (connected && selectedFriend.value) {
    openChatSocket(selectedFriend.value.user_id)
  }
})

watch(showShareDialog, (visible) => {
  if (!visible) {
    selectedSubjectId.value = null
  }
})

onMounted(async () => {
  previousSidebarState.value = sidebarCollapsed.value
  sidebarCollapsed.value = true
  closeMobileNav()
  await loadUserInfo()
  currentUserId.value = Number(getAuthUserId()) || currentUserId.value
  await Promise.all([loadFriendsData(), loadPendingData(), loadShareData()])
  connect()
})

onBeforeUnmount(() => {
  closeChat()
  disconnect()
  sidebarCollapsed.value = previousSidebarState.value
})
</script>

<style scoped>
.friends-shell {
  --app-sidebar-width: clamp(220px, 18vw, 256px);
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(184, 92, 56, 0.12), transparent 24%),
    radial-gradient(circle at 85% 18%, rgba(92, 138, 53, 0.08), transparent 22%),
    linear-gradient(180deg, #f4efe6 0%, #e8dfd0 100%);
}

.friends-shell .desktop-sidebar-handle {
  display: none;
}

.friends-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px 18px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.header-main h1 {
  margin: 0;
  font-size: 30px;
  color: #0f172a;
}

.header-main p {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.7;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.header-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(184, 92, 56, 0.15);
  color: #b85c38;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px;
}

.focus-action {
  border-color: rgba(184, 92, 56, 0.3);
  color: #b85c38;
  background: rgba(184, 92, 56, 0.08);
}

.inline-badge {
  margin-left: 8px;
}

.friends-board {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 20px;
  padding: 20px 28px 28px;
  overflow: hidden;
}

.friends-sidebar {
  flex: 0 0 auto;
  width: min(360px, 40vw);
  min-width: 300px;
}

.chat-stage {
  flex: 1;
  min-width: 0;
}

.friends-sidebar,
.chat-stage {
  min-height: 0;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(18px);
}

.friends-sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 22px 22px 16px;
}

.panel-kicker {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #b85c38;
}

.sidebar-top h2 {
  margin: 0;
  font-size: 24px;
  color: #0f172a;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 0 22px 16px;
}

.summary-card {
  padding: 14px 12px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8f4ec 0%, #f0e6d6 100%);
}

.summary-card.accent {
  background: linear-gradient(180deg, rgba(184, 92, 56, 0.1) 0%, rgba(184, 92, 56, 0.06) 100%);
}

.summary-card.warm {
  background: linear-gradient(180deg, rgba(92, 138, 53, 0.1) 0%, rgba(92, 138, 53, 0.06) 100%);
}

.summary-card span {
  display: block;
  font-size: 12px;
  color: #64748b;
}

.summary-card strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  color: #0f172a;
}

.pane-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 0 22px 16px;
}

.pane-button {
  border: 0;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  padding: 10px 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.pane-button em {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  font-style: normal;
  font-size: 12px;
  line-height: 20px;
  color: #fff;
  background: #b85c38;
}

.pane-button.active {
  background: linear-gradient(135deg, #b85c38 0%, #8d3f1f 100%);
  color: #fff;
  box-shadow: 0 12px 24px rgba(184, 92, 56, 0.2);
}

.sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 22px 22px;
}

.friend-list,
.request-list,
.share-list {
  display: grid;
  gap: 12px;
}

.friend-card,
.request-card,
.share-card,
.search-card {
  width: 100%;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 20px;
  background: #fff;
  padding: 16px;
  text-align: left;
}

.friend-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.friend-card:hover,
.request-card:hover,
.share-card:hover,
.search-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
}

.friend-card.active {
  border-color: #b85c38;
  background: linear-gradient(180deg, rgba(184, 92, 56, 0.08) 0%, #ffffff 100%);
}

.friend-meta,
.friend-meta p {
  min-width: 0;
}

.friend-meta strong,
.request-head strong {
  display: block;
  color: #0f172a;
  font-size: 15px;
}

.friend-meta span,
.request-head span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.friend-meta p,
.request-card p,
.share-card p,
.search-card p {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.6;
}

.friend-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.request-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.request-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.share-card.pending {
  border-color: rgba(184, 92, 56, 0.3);
  background: linear-gradient(180deg, rgba(184, 92, 56, 0.04) 0%, #ffffff 100%);
}

.chat-stage {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px 18px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
}

.chat-profile {
  display: flex;
  align-items: center;
  gap: 14px;
}

.chat-profile h3 {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
}

.chat-profile p {
  margin: 6px 0 0;
  color: #64748b;
}

.chat-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.socket-status {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: #e2e8f0;
  color: #475569;
}

.socket-status.connected {
  background: #dcfce7;
  color: #15803d;
}

.socket-status.connecting,
.socket-status.reconnecting {
  background: #fef3c7;
  color: #b45309;
}

.socket-status.offline,
.socket-status.idle {
  background: #fee2e2;
  color: #b91c1c;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(184, 92, 56, 0.1), transparent 18%),
    linear-gradient(180deg, #f8f4ec 0%, #f4efe6 100%);
}

.inline-share-box {
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid rgba(184, 92, 56, 0.2);
  border-radius: 18px;
  background: rgba(184, 92, 56, 0.06);
}

.inline-share-title {
  margin-bottom: 12px;
  font-size: 13px;
  color: #b85c38;
}

.inline-share-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff;
}

.inline-share-card + .inline-share-card {
  margin-top: 10px;
}

.inline-share-card strong {
  display: block;
  color: #0f172a;
}

.inline-share-card span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.message-stream {
  display: grid;
  gap: 14px;
}

.message-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.message-row.self {
  justify-content: flex-end;
}

.message-row.self .message-bubble {
  background: linear-gradient(135deg, #b85c38 0%, #8d3f1f 100%);
  color: #fff;
}

.message-row.self .message-meta {
  color: rgba(255, 255, 255, 0.82);
}

.message-bubble {
  max-width: min(70%, 640px);
  padding: 14px 16px;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}

.message-meta {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  font-size: 12px;
  color: #64748b;
}

.message-composer {
  padding: 18px 24px 22px;
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  background: #fff;
}

.composer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  color: #64748b;
  font-size: 12px;
  gap: 12px;
}

.chat-empty {
  flex: 1;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 32px;
  color: #64748b;
}

.chat-empty .el-icon {
  font-size: 72px;
  color: #d4a574;
}

.chat-empty h3 {
  margin: 16px 0 8px;
  color: #0f172a;
  font-size: 24px;
}

.dialog-stack {
  display: grid;
  gap: 14px;
}

@media (max-width: 1280px) {
  .friends-board {
    padding: 18px;
  }
  .friends-sidebar {
    width: min(340px, 40vw);
  }
}

@media (max-width: 1100px) {
  .friends-board {
    flex-direction: column;
  }
  .friends-sidebar {
    width: 100%;
    min-width: auto;
    max-height: 300px;
  }
}

@media (max-width: 720px) {
  .page-header,
  .friends-board {
    padding-left: 16px;
    padding-right: 16px;
  }

  .page-header {
    padding-top: 18px;
    flex-direction: column;
    align-items: flex-start;
  }

  .chat-header,
  .inline-share-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions,
  .chat-header-actions,
  .request-actions {
    width: 100%;
  }

  .summary-grid,
  .pane-switch {
    grid-template-columns: 1fr;
  }

  .friend-card {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .friend-side {
    grid-column: 1 / -1;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }

  .message-bubble {
    max-width: calc(100% - 52px);
  }

  .composer-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
