import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
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
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_username')
      if (window.location.pathname !== '/auth') {
        window.location.href = '/auth'
      }
    }
    return Promise.reject(error)
  }
)

export const register = async (username, password) => {
  const response = await api.post('/auth/register', { username, password })
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

export const getSubjects = async () => {
  const response = await api.get('/subjects')
  return response.data
}

export const createSubject = async (name) => {
  const response = await api.post('/subjects', { name })
  return response.data
}

export const deleteSubject = async (subjectId) => {
  const response = await api.delete(`/subjects/${subjectId}`)
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

export const addQuestion = async (questionData) => {
  const response = await api.post('/questions', questionData)
  return response.data
}

export const getQuestions = async (skip = 0, limit = 100, subjectId = null, questionType = 'all', importantOnly = false) => {
  const response = await api.get('/questions', {
    params: { skip, limit, subject_id: subjectId, question_type: questionType, important_only: importantOnly }
  })
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

export const saveDeepSeekKey = async (apiKey) => {
  const response = await api.post('/settings/deepseek-key', { api_key: apiKey })
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
  const response = await api.post('/ai/explain', { question_id: questionId })
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

export default api
