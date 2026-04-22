import { NextResponse } from 'next/server'

// 统一响应格式
export function success(data: any, message = 'success') {
  return NextResponse.json({ code: 0, message, data })
}

export function fail(code: number, message: string, status = 400) {
  return NextResponse.json({ code, message, data: null }, { status })
}

export function paginate(list: any[], total: number, pageNum: number, pageSize: number) {
  return { list, total, pageNum, pageSize }
}

// 常用错误码
export const ERR = {
  UNAUTHORIZED:    () => fail(4001, '未登录或token已过期', 401),
  FORBIDDEN:       () => fail(4003, '无权限访问', 403),
  NOT_FOUND:       (msg = '资源不存在') => fail(4004, msg, 404),
  BAD_REQUEST:     (msg = '参数错误') => fail(4001, msg, 400),
  SERVER_ERROR:    (msg = '服务器内部错误') => fail(5000, msg, 500),
  DUPLICATE:       (msg = '资源已存在') => fail(4002, msg, 409),
}
