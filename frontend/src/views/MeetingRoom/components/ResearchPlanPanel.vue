<template>
  <el-card class="research-plan-panel" shadow="never">
    <template #header>
      <div class="panel-header">
        <el-icon><Document /></el-icon>
        <span>研究計畫 ({{ researchPlans.length }})</span>
      </div>
    </template>

    <div v-if="researchPlans.length === 0" class="no-plan">
      <el-empty description="尚無研究計畫" :image-size="80" />
    </div>

    <div v-else class="plan-content">
      <!-- 多個計畫折疊面板 -->
      <el-collapse v-model="activePlanIds">
        <el-collapse-item
          v-for="plan in researchPlans"
          :key="plan.plan_id"
          :name="plan.plan_id"
        >
          <template #title>
            <div class="plan-header">
              <span class="plan-number">計畫 #{{ plan.plan_id }}</span>
              <el-tag :type="getTriggerType(plan.trigger_reason)" size="small">
                {{ getTriggerText(plan.trigger_reason) }}
              </el-tag>
              <span v-if="plan.requester" class="requester">
                by {{ plan.requester }}
              </span>
            </div>
          </template>

          <!-- 計畫內容 -->
          <div class="plan-details">
            <!-- 計畫目標 -->
            <div class="plan-objective">
              <h5>🎯 目標</h5>
              <p>{{ plan.objective }}</p>
            </div>

            <!-- 執行步驟 -->
            <div class="plan-steps">
              <h5>🔧 執行步驟 ({{ getPlanSteps(plan).length }})</h5>
              <el-timeline size="small">
                <el-timeline-item
                  v-for="(step, index) in getPlanSteps(plan)"
                  :key="step.step_id"
                  :type="getStepType(step)"
                  :icon="getStepIcon(step)"
                  :color="getStepColor(step)"
                >
                  <div class="step-header">
                    <span class="step-number">步驟 {{ index + 1 }}</span>
                    <el-tag :type="getStatusTagType(step.status)" size="small">
                      {{ getStatusText(step.status) }}
                    </el-tag>
                  </div>
                  
                  <div class="step-tool">
                    <strong>{{ step.tool_name }}</strong>
                  </div>
                  
                  <div class="step-result" v-if="step.status === 'completed'">
                    <el-icon :color="getQualityColor(step.quality)"><SuccessFilled /></el-icon>
                    <span>品質: <strong>{{ step.quality }}</strong></span>
                  </div>

                  <div class="step-error" v-if="step.status === 'error'">
                    <el-alert type="error" :closable="false" show-icon size="small">
                      {{ step.error }}
                    </el-alert>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watchEffect } from 'vue'
import { Document, SuccessFilled } from '@element-plus/icons-vue'
import { useMeetingStore, type ResearchStep, type ResearchPlan } from '@/stores/meeting'

const meetingStore = useMeetingStore()

const researchPlans = computed(() => meetingStore.researchPlans)

// 預設展開最新計畫
const activePlanIds = ref<number[]>([])

// 當有新計畫時自動展開
watchEffect(() => {
  if (meetingStore.currentPlanId && !activePlanIds.value.includes(meetingStore.currentPlanId)) {
    activePlanIds.value.push(meetingStore.currentPlanId)
  }
})

function getPlanSteps(plan: ResearchPlan): ResearchStep[] {
  if (!plan.steps) return []
  return plan.steps.map(step => {
    const stepState = meetingStore.planSteps.get(step.step_id)
    return stepState || step
  })
}

function getTriggerType(reason?: string): string {
  switch (reason) {
    case 'initial': return ''
    case 'expert_request': return 'warning'
    default: return 'info'
  }
}

function getTriggerText(reason?: string): string {
  switch (reason) {
    case 'initial': return '初始'
    case 'expert_request': return '專家請求'
    default: return '其他'
  }
}

function getStepType(step: ResearchStep): string {
  switch (step.status) {
    case 'completed': return 'success'
    case 'error': return 'danger'
    case 'running': return 'primary'
    default: return 'info'
  }
}

function getStepIcon(step: ResearchStep): any {
  switch (step.status) {
    case 'completed': return SuccessFilled
    case 'error': return 'CircleClose'
    case 'running': return 'Loading'
    default: return 'Clock'
  }
}

function getStepColor(step: ResearchStep): string {
  switch (step.status) {
    case 'completed': return '#67c23a'
    case 'error': return '#f56c6c'
    case 'running': return '#409eff'
    default: return '#909399'
  }
}

function getStatusTagType(status?: string): string {
  switch (status) {
    case 'completed': return 'success'
    case 'error': return 'danger'
    case 'running': return 'primary'
    default: return 'info'
  }
}

function getStatusText(status?: string): string {
  switch (status) {
    case 'completed': return '已完成'
    case 'error': return '失敗'
    case 'running': return '執行中'
    default: return '待執行'
  }
}

function getQualityColor(quality?: string): string {
  switch (quality?.toUpperCase()) {
    case 'REALTIME': return '#67c23a'
    case 'EOD': return '#409eff'
    case 'DELAYED': return '#e6a23c'
    case 'MISSING': return '#909399'
    default: return '#909399'
  }
}
</script>

<style scoped lang="scss">
.research-plan-panel {
  height: 100%;
  background-color: var(--el-bg-color);
  
  :deep(.el-card__header) {
    padding: 12px 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  :deep(.el-card__body) {
    padding: 16px;
    height: calc(100% - 50px);
    overflow-y: auto;
  }
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.no-plan {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.plan-content {
  :deep(.el-collapse) {
    border: none;
  }

  :deep(.el-collapse-item__header) {
    font-size: 13px;
    font-weight: 500;
    background-color: var(--el-fill-color-lighter);
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 8px;
  }

  :deep(.el-collapse-item__wrap) {
    border: none;
  }
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  
  .plan-number {
    font-weight: 600;
  }
  
  .requester {
    margin-left: auto;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

.plan-details {
  padding: 12px 0;
  
  h5 {
    margin: 0 0 8px;
    font-size: 13px;
    font-weight: 600;
  }
}

.plan-objective {
  margin-bottom: 16px;
  
  p {
    margin: 0;
    padding: 10px;
    background-color: var(--el-fill-color-light);
    border-radius: 4px;
    font-size: 12px;
    line-height: 1.5;
  }
}

.plan-steps {
  :deep(.el-timeline) {
    padding-left: 0;
  }
  
  :deep(.el-timeline-item__wrapper) {
    padding-left: 20px;
  }
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  
  .step-number {
    font-weight: 600;
    font-size: 12px;
  }
}

.step-tool {
  margin-bottom: 6px;
  font-size: 13px;
}

.step-result {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding: 6px 10px;
  background-color: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 11px;
  
  strong {
    color: var(--el-color-primary);
  }
}

.step-error {
  margin-top: 6px;
  
  :deep(.el-alert) {
    font-size: 11px;
  }
}
</style>
