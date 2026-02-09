import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface AgentMessage {
    agent_id: string
    agent_name: string
    role: string
    content: string
    msg_type: string
    round: number
    timestamp: string
}

export interface MeetingEvent {
    event_type: string
    payload: any
}

export const useMeetingStore = defineStore('meeting', () => {
    const activeSymbol = ref('')
    const messages = ref<AgentMessage[]>([])
    const isSimulating = ref(false)
    const currentStatus = ref('')

    const getMessages = computed(() => messages.value)

    function setSymbol(symbol: string) {
        activeSymbol.value = symbol
        messages.value = []
        isSimulating.value = false
        currentStatus.value = ''
    }

    function addMessage(msg: AgentMessage) {
        messages.value.push(msg)
    }

    function setSimulating(status: boolean) {
        isSimulating.value = status
    }

    function setStatus(status: string) {
        currentStatus.value = status
    }

    function clearHistory() {
        messages.value = []
    }

    function handleEvent(event: MeetingEvent) {
        const { event_type, payload } = event

        switch (event_type) {
            case 'status':
                currentStatus.value = payload.message || ''
                break
            case 'message':
                addMessage(payload)
                break
            case 'state_change':
                if (payload.status === 'done' || payload.status === 'error') {
                    isSimulating.value = false
                }
                break
            case 'error':
                currentStatus.value = `Error: ${payload.message}`
                isSimulating.value = false
                break
        }
    }

    return {
        activeSymbol,
        messages,
        isSimulating,
        currentStatus,
        getMessages,
        setSymbol,
        addMessage,
        setSimulating,
        setStatus,
        clearHistory,
        handleEvent
    }
})
