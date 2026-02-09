import { ApiClient, type ApiResponse } from './request'

export interface StartMeetingRequest {
    symbol_key: string
    query: string
    mention_ids?: string[]
    reply_to_id?: string
}

export interface MeetingSessionMessages {
    messages: any[]
}

export const meetingApi = {
    /**
     * 發起會議
     */
    startMeeting: (data: StartMeetingRequest): Promise<ApiResponse<any>> => {
        return ApiClient.post('/api/meeting/start', data)
    },

    /**
     * 獲取會議消息歷史
     */
    getSessionMessages: (symbolKey: string): Promise<ApiResponse<MeetingSessionMessages>> => {
        return ApiClient.get(`/api/meeting/messages/${symbolKey}`)
    },

    /**
     * 清空會議歷史
     */
    clearHistory: (symbolKey: string): Promise<ApiResponse<any>> => {
        return ApiClient.delete(`/api/meeting/messages/${symbolKey}`)
    }
}

export default meetingApi
