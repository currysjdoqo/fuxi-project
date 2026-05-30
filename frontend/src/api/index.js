import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

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

export const submitAnswer = async (questionId, userAnswer) => {
  const response = await api.post('/practice/submit', {
    question_id: questionId,
    user_answer: userAnswer
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

export const submitReviewAnswer = async (questionId, userAnswer) => {
  const response = await api.post('/review/submit', {
    question_id: questionId,
    user_answer: userAnswer,
    is_review_mode: true
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

export const clearAllData = async () => {
  const response = await api.delete('/data')
  return response.data
}

export const getAiExplanation = async (questionId) => {
  const response = await api.post('/ai/explain', { question_id: questionId })
  return response.data
}

export default api
