import axios from 'axios'
import { clearAuthSession, getAuthToken } from '../utils/authStorage'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuthSession()
      if (window.location.pathname !== '/auth') {
        window.location.href = '/auth'
      }
    }
    return Promise.reject(error)
  }
)

export const register = async (username, password, inviteCode = '') => {
  const response = await api.post('/auth/register', { username, password, invite_code: inviteCode })
  return response.data
}

export const login = async (username, password) => {
  const response = await api.post('/auth/login', { username, password })
  return response.data
}

export const getCurrentUser = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

export const updateProfile = async (signature) => {
  const response = await api.put('/auth/profile', { signature })
  return response.data
}

export const uploadAvatar = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/auth/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export const changePassword = async (oldPassword, newPassword) => {
  const response = await api.post('/auth/password', {
    old_password: oldPassword,
    new_password: newPassword
  })
  return response.data
}

export const getSubjects = async () => {
  const response = await api.get('/subjects')
  return response.data
}

export const createSubject = async (name, folderId = null) => {
  const body = { name }
  if (folderId !== null) body.folder_id = folderId
  const response = await api.post('/subjects', body)
  return response.data
}

// ---- Folder API ----
export const getFolders = async () => {
  const response = await api.get('/folders')
  return response.data
}

export const getFoldersWithSubjects = async () => {
  const response = await api.get('/folders/with-subjects')
  return response.data
}

export const createFolder = async (name) => {
  const response = await api.post('/folders', { name })
  return response.data
}

export const updateFolder = async (folderId, data) => {
  const response = await api.patch(`/folders/${folderId}`, data)
  return response.data
}

export const deleteFolder = async (folderId) => {
  const response = await api.delete(`/folders/${folderId}`)
  return response.data
}

export const addSubjectToFolder = async (folderId, subjectId) => {
  const response = await api.post(`/folders/${folderId}/subjects/${subjectId}`)
  return response.data
}

export const removeSubjectFromFolder = async (folderId, subjectId) => {
  const response = await api.delete(`/folders/${folderId}/subjects/${subjectId}`)
  return response.data
}

export const deleteSubject = async (subjectId) => {
  const response = await api.delete(`/subjects/${subjectId}`)
  return response.data
}

export const getChapters = async (subjectId) => {
  const response = await api.get(`/subjects/${subjectId}/chapters`)
  return response.data
}

export const createChapter = async (subjectId, name) => {
  const response = await api.post('/chapters', { subject_id: subjectId, name })
  return response.data
}

export const updateChapter = async (chapterId, data) => {
  const response = await api.patch(`/chapters/${chapterId}`, data)
  return response.data
}

export const deleteChapter = async (chapterId) => {
  const response = await api.delete(`/chapters/${chapterId}`)
  return response.data
}

export const moveQuestionsToChapter = async (chapterId, questionIds) => {
  const response = await api.post('/chapters/batch-move', {
    chapter_id: chapterId,
    question_ids: questionIds
  })
  return response.data
}

export const aiAssignChapters = async (subjectId, questions) => {
  const response = await api.post('/import/ai-assign-chapters', {
    subject_id: subjectId,
    questions
  })
  return response.data
}

// AI 知识点提炼
export const tagChapterQuestions = async (chapterId) => {
  const response = await api.post(`/chapters/${chapterId}/tag-questions`)
  return response.data
}

export const generateChapterSummary = async (chapterId) => {
  const response = await api.post(`/chapters/${chapterId}/generate-summary`)
  return response.data
}

export const generateChapterOutline = async (chapterId) => {
  const response = await api.post(`/chapters/${chapterId}/generate-outline`)
  return response.data
}

export const getChapterKnowledge = async (chapterId) => {
  const response = await api.get(`/chapters/${chapterId}/knowledge`)
  return response.data
}

export const extractAllKnowledge = async (chapterId) => {
  const response = await api.post(`/chapters/${chapterId}/extract-all`)
  return response.data
}

export const getUnassignedQuestions = async (subjectId) => {
  const response = await api.get(`/subjects/${subjectId}/unassigned-questions`)
  return response.data
}

export const aiAssignUnassigned = async (subjectId) => {
  const response = await api.post(`/subjects/${subjectId}/ai-assign-unassigned`)
  return response.data
}

export const importQuestions = async (text, subjectId) => {
  const response = await api.post('/import', {
    text,
    subject_id: subjectId
  })
  return response.data
}

export const parseQuestions = async (text) => {
  const response = await api.post('/import/parse', { text })
  return response.data
}

export const extractTextFromFile = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/import/extract-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export const extractMultipleFiles = async (files) => {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })
  const response = await api.post('/import/extract-multiple', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export const importParsedQuestions = async (questions, subjectId) => {
  const response = await api.post('/import', {
    subject_id: subjectId,
    questions
  })
  return response.data
}

export const downloadImportTemplate = async () => {
  const response = await api.get('/import/template', {
    responseType: 'blob'
  })
  return response.data
}

export const parseUploadedFile = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/import/parse-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export const smartParseText = async (text, { sourceName = '', aiFallback = false, forceResiduals = false } = {}) => {
  const response = await api.post('/import/smart-parse', {
    text,
    source_name: sourceName,
    ai_fallback: aiFallback,
    force_residuals: forceResiduals
  })
  return response.data
}

export const smartParseFile = async (file, { aiFallback = false, forceResiduals = false } = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/import/smart-parse-file', formData, {
    params: { ai_fallback: aiFallback, force_residuals: forceResiduals },
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export const batchParseFiles = async (files) => {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })
  const response = await api.post('/import/batch-parse', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export const addQuestion = async (questionData) => {
  const response = await api.post('/questions', questionData)
  return response.data
}

export const getQuestions = async (skip = 0, limit = 100, subjectId = null, questionType = 'all', importantOnly = false, chapterId = null) => {
  const response = await api.get('/questions', {
    params: { skip, limit, subject_id: subjectId, question_type: questionType, important_only: importantOnly, chapter_id: chapterId }
  })
  return response.data
}

export const getQuestionsSummary = async (subjectId = null, questionType = 'all', importantOnly = false, chapterId = null) => {
  const response = await api.get('/questions/summary', {
    params: { subject_id: subjectId, question_type: questionType, important_only: importantOnly, chapter_id: chapterId }
  })
  return response.data
}

export const getQuestionDetail = async (questionId) => {
  const response = await api.get(`/questions/${questionId}/detail`)
  return response.data
}

export const deleteQuestion = async (questionId) => {
  const response = await api.delete(`/questions/${questionId}`)
  return response.data
}

export const batchDeleteQuestions = async (questionIds) => {
  const response = await api.post('/questions/batch-delete', {
    question_ids: questionIds
  })
  return response.data
}

export const updateQuestionType = async (questionId, type) => {
  const response = await api.patch(`/questions/${questionId}/type`, { type })
  return response.data
}

export const updateQuestionImportant = async (questionId, isImportant) => {
  const response = await api.patch(`/questions/${questionId}/important`, {
    is_important: isImportant
  })
  return response.data
}

export const updateQuestionAnswer = async (questionId, answer) => {
  const response = await api.patch(`/questions/${questionId}/answer`, {
    answer
  })
  return response.data
}

export const updateQuestionOptions = async (questionId, options) => {
  const response = await api.patch(`/questions/${questionId}/options`, {
    options
  })
  return response.data
}

export const getTrashQuestions = async (subjectId = null) => {
  const response = await api.get('/trash', {
    params: { subject_id: subjectId }
  })
  return response.data
}

export const restoreTrashQuestions = async (questionIds) => {
  const response = await api.post('/trash/restore', {
    question_ids: questionIds
  })
  return response.data
}

export const permanentlyDeleteQuestion = async (questionId) => {
  const response = await api.delete(`/trash/${questionId}`)
  return response.data
}

export const permanentlyDeleteTrashQuestions = async (questionIds) => {
  const response = await api.post('/trash/permanent-delete', {
    question_ids: questionIds
  })
  return response.data
}

export const submitAnswer = async (questionId, userAnswer, selfEvaluation = null) => {
  const response = await api.post('/practice/submit', {
    question_id: questionId,
    user_answer: userAnswer,
    self_evaluation: selfEvaluation
  })
  return response.data
}

export const batchSubmitAnswers = async (submissions) => {
  const response = await api.post('/practice/batch-submit', {
    submissions
  })
  return response.data
}

export const batchSubmitReviewAnswers = async (submissions) => {
  const response = await api.post('/review/batch-submit', {
    submissions
  })
  return response.data
}

export const getWrongQuestions = async (subjectId = null) => {
  const response = await api.get('/wrong-questions', {
    params: { subject_id: subjectId }
  })
  return response.data
}

export const removeWrongQuestion = async (questionId) => {
  const response = await api.delete(`/wrong-questions/${questionId}`)
  return response.data
}

export const generateReviewQuestions = async (count, subjectId = null) => {
  const response = await api.post('/review/generate', {
    count,
    subject_id: subjectId
  })
  return response.data
}

export const updateQuestionExplanation = async (questionId, explanation) => {
  const response = await api.post('/review/update-explanation', {
    question_id: questionId,
    explanation: explanation
  })
  return response.data
}

export const submitReviewAnswer = async (questionIdOrPayload, userAnswer) => {
  const payload = typeof questionIdOrPayload === 'object' && questionIdOrPayload !== null
    ? {
      question_id: questionIdOrPayload.question_id,
      user_answer: questionIdOrPayload.user_answer,
      is_review_mode: questionIdOrPayload.is_review_mode ?? true
    }
    : {
      question_id: questionIdOrPayload,
      user_answer: userAnswer,
      is_review_mode: true
    }

  const response = await api.post('/review/submit', {
    question_id: payload.question_id,
    user_answer: payload.user_answer,
    is_review_mode: payload.is_review_mode
  })
  return response.data
}

export const getSettings = async () => {
  const response = await api.get('/settings')
  return response.data
}

export const saveCustomAiKey = async (apiKey) => {
  const response = await api.post('/settings/custom-ai-key', { api_key: apiKey })
  return response.data
}

export const deleteCustomAiKey = async () => {
  const response = await api.delete('/settings/custom-ai-key')
  return response.data
}

export const getBillingStatus = async () => {
  const response = await api.get('/billing/status')
  return response.data
}

export const createPaymentOrder = async (payload) => {
  const response = await api.post('/billing/payments/create', payload)
  return response.data
}

export const getPaymentOrder = async (orderNo) => {
  const response = await api.get(`/billing/payments/${orderNo}`)
  return response.data
}

export const exchangeCredits = async (amountCents) => {
  const response = await api.post('/billing/credits/exchange', { amount_cents: amountCents })
  return response.data
}

export const saveWrongThreshold = async (threshold) => {
  const response = await api.post('/settings/wrong-threshold', { threshold })
  return response.data
}

export const clearAllData = async (password) => {
  const response = await api.delete('/data', {
    data: { password }
  })
  return response.data
}

export const getAiExplanation = async (questionId) => {
  const response = await api.get('/ai/explain', {
    params: { question_id: questionId }
  })
  return response.data
}

export const checkAiApiStatus = async () => {
  const response = await api.get('/ai/check')
  return response.data
}

// 计划相关API
export const createPlanItem = async (date, content) => {
  const response = await api.post('/plan/items', { date, content })
  return response.data
}

export const getPlanItemsByDate = async (date) => {
  const response = await api.get(`/plan/items/${date}`)
  return response.data
}

export const getPlanItemsByRange = async (startDate, endDate) => {
  const response = await api.get(`/plan/items/range/${startDate}/${endDate}`)
  return response.data
}

export const updatePlanItem = async (itemId, data) => {
  const response = await api.put(`/plan/items/${itemId}`, data)
  return response.data
}

export const deletePlanItem = async (itemId) => {
  const response = await api.delete(`/plan/items/${itemId}`)
  return response.data
}

// 导出相关API
export const getExportFormats = async () => {
  const response = await api.get('/export/formats')
  return response.data
}

export const getExportTypes = async () => {
  const response = await api.get('/export/types')
  return response.data
}

export const getExportInfo = async (subjectId) => {
  const response = await api.get('/export/info', {
    params: { subject_id: subjectId }
  })
  return response.data
}

export const previewExport = async (subjectId, format = 'word', includeAnswer = true, includeAnalysis = true) => {
  const response = await api.get('/export/preview', {
    params: {
      subject_id: subjectId,
      format,
      include_answer: includeAnswer,
      include_analysis: includeAnalysis
    }
  })
  return response.data
}

export const exportQuestions = async (subjectId, options = {}) => {
  const {
    format = 'word',
    includeAnswer = true,
    includeAnalysis = true,
    questionTypes = null
  } = options

  const params = new URLSearchParams()
  params.append('subject_id', subjectId)
  params.append('format', format)
  params.append('include_answer', includeAnswer)
  params.append('include_analysis', includeAnalysis)
  if (questionTypes && questionTypes.length > 0) {
    params.append('question_types', questionTypes.join(','))
  }

  const response = await api.get('/export/download', {
    params,
    responseType: 'blob'
  })
  return response.data
}

export const exportChapterReview = async (chapterIds, format, filename) => {
  const response = await api.post('/export/chapters', {
    chapter_ids: chapterIds,
    format,
    filename
  }, {
    responseType: 'blob'
  })
  return response
}

// 好友相关API
export const sendFriendRequest = async (userCode) => {
  const response = await api.post('/friends/request', { user_code: userCode })
  return response.data
}

export const acceptFriendRequest = async (friendId) => {
  const response = await api.post('/friends/accept', { friend_id: friendId })
  return response.data
}

export const rejectFriendRequest = async (friendId) => {
  const response = await api.post('/friends/reject', { friend_id: friendId })
  return response.data
}

export const getFriends = async () => {
  const response = await api.get('/friends/list')
  return response.data
}

export const getPendingRequests = async () => {
  const response = await api.get('/friends/pending')
  return response.data
}

export const removeFriend = async (friendId) => {
  const response = await api.delete(`/friends/${friendId}`)
  return response.data
}

export const searchUser = async (code) => {
  const response = await api.get('/users/search', { params: { code } })
  return response.data
}

// 消息相关API
export const sendMessage = async (receiverId, content) => {
  const response = await api.post('/messages/send', { receiver_id: receiverId, content })
  return response.data
}

export const getMessages = async (friendId) => {
  const response = await api.get(`/messages/${friendId}`)
  return response.data
}

export const markMessagesRead = async (friendId) => {
  const response = await api.post(`/messages/read/${friendId}`)
  return response.data
}

export const getUnreadCount = async () => {
  const response = await api.get('/messages/unread-count')
  return response.data
}

// 分享相关API
export const shareSubject = async (subjectId, friendId) => {
  const response = await api.post('/share/subject', { subject_id: subjectId, friend_id: friendId })
  return response.data
}

export const getShareList = async () => {
  const response = await api.get('/share/list')
  return response.data
}

export const acceptShare = async (shareId) => {
  const response = await api.post(`/share/accept/${shareId}`)
  return response.data
}

export const rejectShare = async (shareId) => {
  const response = await api.post(`/share/reject/${shareId}`)
  return response.data
}

export default api
