const normalizeDetail = (detail, defaultMsg) => {
  if (!detail) return defaultMsg

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item?.msg) return item.msg
        if (item?.message) return item.message
        return null
      })
      .filter(Boolean)

    return messages.length ? messages.join('; ') : defaultMsg
  }

  if (typeof detail === 'object') {
    if (typeof detail.msg === 'string') return detail.msg
    if (typeof detail.message === 'string') return detail.message

    try {
      return JSON.stringify(detail)
    } catch {
      return defaultMsg
    }
  }

  return String(detail)
}

export const getErrorMessage = (error, defaultMsg = '操作失败') => {
  if (error?.response) {
    const { data, statusText } = error.response

    if (data && typeof data === 'object' && 'detail' in data) {
      return normalizeDetail(data.detail, defaultMsg)
    }

    if (typeof data === 'string') {
      return data
    }

    if (statusText) {
      return statusText
    }
  }

  if (error?.message && typeof error.message === 'string') {
    return error.message
  }

  if (typeof error === 'string') {
    return error
  }

  return defaultMsg
}
