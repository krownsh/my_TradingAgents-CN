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

export interface ResearchStep {
    step_id: string
    tool_name: string
    args_schema: Record<string, any>
    expected_output: string
    validation_rules: string[]
    status?: 'pending' | 'running' | 'completed' | 'error'
    quality?: string
    has_data?: boolean
    error?: string
}

export interface ResearchPlan {
    plan_id?: number
    objective: string
    constraints: Record<string, any>
    steps: ResearchStep[]
    symbol_key?: string
    trigger_reason?: string
    requester?: string
}

export const useMeetingStore = defineStore('meeting', () => {
    const activeSymbol = ref('')
    const messages = ref<AgentMessage[]>([])
    const isSimulating = ref(false)
    const currentStatus = ref('')

    // Dexter Research Plan State - 支援多個計畫
    const researchPlans = ref<ResearchPlan[]>([])
    const currentPlanId = ref<number | null>(null)
    const planSteps = ref<Map<string, ResearchStep>>(new Map())

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
            case 'plan_generated':
                // Dexter 計畫生成事件 - 支援多個計畫
                const newPlan: ResearchPlan = {
                    plan_id: payload.plan_id,
                    objective: payload.objective,
                    constraints: payload.constraints || {},
                    steps: payload.steps || [],
                    symbol_key: payload.symbol_key,
                    trigger_reason: payload.trigger_reason,
                    requester: payload.requester
                }
                researchPlans.value.push(newPlan)
                currentPlanId.value = payload.plan_id

                // 初始化步驟狀態
                if (newPlan.steps) {
                    newPlan.steps.forEach((step: any) => {
                        planSteps.value.set(step.step_id, {
                            ...step,
                            status: 'pending'
                        })
                    })
                }
                break
            case 'tool_start':
                // 工具開始執行
                const startStepId = payload.step_id
                if (planSteps.value.has(startStepId)) {
                    const step = planSteps.value.get(startStepId)!
                    step.status = 'running'
                    planSteps.value.set(startStepId, { ...step })
                }
                break
            case 'tool_complete':
                // 工具執行完成
                const completeStepId = payload.step_id
                if (planSteps.value.has(completeStepId)) {
                    const step = planSteps.value.get(completeStepId)!
                    step.status = 'completed'
                    step.quality = payload.quality
                    step.has_data = payload.has_data
                    planSteps.value.set(completeStepId, { ...step })
                }
                break
            case 'tool_error':
                // 工具執行錯誤
                const errorStepId = payload.step_id
                if (planSteps.value.has(errorStepId)) {
                    const step = planSteps.value.get(errorStepId)!
                    step.status = 'error'
                    step.error = payload.error
                    planSteps.value.set(errorStepId, { ...step })
                }
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
        researchPlans,
        currentPlanId,
        planSteps,
        getMessages,
        setSymbol,
        addMessage,
        setSimulating,
        setStatus,
        clearHistory,
        handleEvent
    }
})
