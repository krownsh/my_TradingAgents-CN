<template>
  <el-card class="agent-status-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span>分析進度</span>
      </div>
    </template>
    
    <div class="status-content">
      <div v-if="meetingStore.isSimulating" class="active-status">
        <div class="current-agent">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在進行: {{ meetingStore.currentStatus }}</span>
        </div>
        
        <el-divider />
        
        <div class="progress-steps">
          <!-- We can add more detailed steps here if needed -->
          <div class="step-item active">
            <el-icon><Monitor /></el-icon>
            <span>意圖分析</span>
          </div>
          <div class="step-line"></div>
          <div class="step-item">
            <el-icon><User /></el-icon>
            <span>專家討論</span>
          </div>
          <div class="step-line"></div>
          <div class="step-item">
            <el-icon><Document /></el-icon>
            <span>報告生成</span>
          </div>
        </div>
      </div>
      
      <div v-else class="idle-status">
        <el-empty :image-size="40" description="當前無活動會議" />
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { useMeetingStore } from '@/stores/meeting'
import { Loading, Monitor, User, Document } from '@element-plus/icons-vue'

const meetingStore = useMeetingStore()
</script>

<style scoped lang="scss">
.agent-status-card {
  height: 100%;
}

.status-content {
  display: flex;
  flex-direction: column;
}

.current-agent {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  color: var(--el-color-primary);
}

.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 10px 0;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--el-text-color-secondary);
  
  &.active {
    color: var(--el-color-primary);
    font-weight: bold;
  }
}

.step-line {
  width: 1px;
  height: 20px;
  background-color: var(--el-border-color);
  margin-left: 10px;
}
</style>
