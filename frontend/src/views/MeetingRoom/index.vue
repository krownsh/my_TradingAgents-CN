<template>
  <div class="meeting-room-container">
    <div class="meeting-layout">
      <!-- Left: Stock List / Context -->
      <div class="stock-context-panel">
        <el-card class="context-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>股票內容</span>
            </div>
          </template>
          <div class="stock-info" v-if="activeStock">
            <h2 class="stock-name">{{ activeStock.name }}</h2>
            <div class="stock-code">{{ activeStock.code }}</div>
            <div class="price-info" :class="priceClass">
              <span class="price">{{ activeStock.price }}</span>
              <span class="change">{{ activeStock.change > 0 ? '+' : '' }}{{ activeStock.change }}%</span>
            </div>
          </div>
          <div v-else class="no-stock">
            <el-empty description="請先選擇分析股票" :image-size="60" />
          </div>
        </el-card>
      </div>

      <!-- Center: Meeting Chat -->
      <div class="meeting-chat-panel">
        <MeetingChat />
      </div>

      <!-- Right: Agent Status / Tools -->
      <div class="agent-status-panel">
        <AgentStatus />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMeetingStore } from '@/stores/meeting'
import MeetingChat from './components/MeetingChat.vue'
import AgentStatus from './components/AgentStatus.vue'
import { useAppStore } from '@/stores/app'

const meetingStore = useMeetingStore()
const appStore = useAppStore()

// Mock data for now, ideally fetched from a stock store
const activeStock = ref({
  name: 'NVIDIA',
  code: 'US:NVDA',
  price: 721.33,
  change: 1.25
})

const priceClass = computed(() => {
  if (!activeStock.value) return ''
  return activeStock.value.change >= 0 ? 'up' : 'down'
})

let ws: WebSocket | null = null

const initWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // In dev, VITE_API_BASE_URL might be http://localhost:8000
  let baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
  baseUrl = baseUrl.replace(/^http/, 'ws')
  
  const wsUrl = `${baseUrl}/api/meeting/ws`
  console.log('Connecting to Meeting WebSocket:', wsUrl)

  ws = new WebSocket(wsUrl)
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      meetingStore.handleEvent(data)
    } catch (e) {
      console.error('Failed to parse WS message:', e)
    }
  }

  ws.onopen = () => {
    console.log('Meeting WebSocket connected')
  }

  ws.onclose = () => {
    console.log('Meeting WebSocket disconnected')
  }
}

onMounted(() => {
  meetingStore.setSymbol(activeStock.value.code)
  initWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped lang="scss">
.meeting-room-container {
  height: calc(100vh - 120px);
  padding: 16px;
  background-color: var(--el-bg-color-page);
}

.meeting-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

.stock-context-panel {
  width: 260px;
  flex-shrink: 0;
  
  .context-card {
    height: 100%;
    background-color: var(--el-bg-color);
  }
}

.meeting-chat-panel {
  flex: 1;
  min-width: 0;
  height: 100%;
}

.agent-status-panel {
  width: 280px;
  flex-shrink: 0;
  height: 100%;
}

.stock-info {
  text-align: center;
  padding: 10px 0;

  .stock-name {
    margin: 0;
    font-size: 1.5rem;
  }

  .stock-code {
    color: var(--el-text-color-secondary);
    font-size: 0.9rem;
    margin-bottom: 12px;
  }

  .price-info {
    font-weight: bold;
    font-size: 1.25rem;
    
    display: flex;
    flex-direction: column;
    gap: 4px;

    &.up { color: var(--el-color-danger); }
    &.down { color: var(--el-color-success); }
  }
}
</style>
