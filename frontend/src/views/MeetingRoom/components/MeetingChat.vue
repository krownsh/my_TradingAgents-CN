<template>
  <div class="chat-container">
    <div class="message-list" ref="messageListRef">
      <div v-if="meetingStore.messages.length === 0" class="empty-state">
        <el-empty description="歡迎來到研究會議室，輸入問題開始分析" />
      </div>
      
      <div v-for="(msg, index) in meetingStore.messages" :key="index" 
           class="message-item" :class="getMessageClass(msg)">
        <div class="message-avatar">
          <el-avatar :size="40" :icon="getAvatarIcon(msg)">
            {{ msg.agent_name.charAt(0) }}
          </el-avatar>
        </div>
        <div class="message-content-wrapper">
          <div class="message-header">
            <span class="agent-name">{{ msg.agent_name }}</span>
            <span class="agent-role" v-if="msg.role">{{ msg.role }}</span>
            <span class="timestamp">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="message-bubble" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>
    </div>

    <div class="chat-input-area">
      <div class="input-wrapper">
        <el-input
          v-model="userInput"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          placeholder="輸入與股票相關的問題，例如：'分析這家公司的技術面趨勢'"
          @keydown.enter.prevent="handleSend"
          :disabled="meetingStore.isSimulating"
        />
        <div class="input-actions">
          <el-button 
            type="primary" 
            :icon="Promotion" 
            circle 
            size="large"
            :loading="meetingStore.isSimulating"
            @click="handleSend"
            :disabled="!userInput.trim()"
          />
          <el-button 
            type="info" 
            :icon="Delete" 
            circle 
            size="large"
            title="清空歷史"
            @click="handleClear"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUpdated, nextTick } from 'vue'
import { useMeetingStore } from '@/stores/meeting'
import { meetingApi } from '@/api/meeting'
import { Promotion, Delete, User, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'

const meetingStore = useMeetingStore()
const userInput = ref('')
const messageListRef = ref<HTMLElement | null>(null)

const getMessageClass = (msg: any) => {
  return msg.agent_id === 'user' ? 'user-message' : 'agent-message'
}

const getAvatarIcon = (msg: any) => {
  if (msg.agent_id === 'user') return User
  return ChatDotRound
}

const formatTime = (ts: string) => {
  if (!ts) return ''
  const date = new Date(ts)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const renderMarkdown = (content: string) => {
  return marked(content)
}

const scrollToBottom = () => {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const handleSend = async () => {
  if (!userInput.value.trim() || meetingStore.isSimulating) return
  
  const query = userInput.value
  userInput.value = ''
  
  // Optimistically add user message
  const userMsg = {
    agent_id: 'user',
    agent_name: '我',
    role: '投資者',
    content: query,
    msg_type: 'query',
    round: 0,
    timestamp: new Date().toISOString()
  }
  meetingStore.addMessage(userMsg)
  meetingStore.setSimulating(true)
  
  try {
    await meetingApi.startMeeting({
      symbol_key: meetingStore.activeSymbol,
      query: query
    })
  } catch (e: any) {
    ElMessage.error(e.message || '啟動會議失敗')
    meetingStore.setSimulating(false)
  }
}

const handleClear = async () => {
  try {
    await ElMessageBox.confirm('確定要清空會議歷史嗎？', '提醒', {
      type: 'warning'
    })
    await meetingApi.clearHistory(meetingStore.activeSymbol)
    meetingStore.clearHistory()
    ElMessage.success('歷史已清空')
  } catch (e) {
    // Cancelled or error
  }
}

onUpdated(() => {
  nextTick(scrollToBottom)
})
</script>

<style scoped lang="scss">
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--el-bg-color);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 85%;

  &.user-message {
    align-self: flex-end;
    flex-direction: row-reverse;
    
    .message-bubble {
      background-color: var(--el-color-primary-light-9);
      border-color: var(--el-color-primary-light-7);
    }
  }
  
  &.agent-message {
    align-self: flex-start;
  }
}

.message-avatar {
  flex-shrink: 0;
}

.message-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  
  .agent-name {
    font-weight: bold;
  }
  
  .agent-role {
    color: var(--el-text-color-secondary);
    background-color: var(--el-fill-color-light);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.75rem;
  }
  
  .timestamp {
    color: var(--el-text-color-placeholder);
    font-size: 0.75rem;
  }
}

.message-bubble {
  padding: 12px 16px;
  background-color: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  font-size: 0.95rem;
  line-height: 1.6;
  
  :deep(p) { margin: 8px 0; &:first-child { margin-top: 0; } &:last-child { margin-bottom: 0; } }
  :deep(code) { background-color: var(--el-fill-color-dark); padding: 2px 4px; border-radius: 4px; font-family: monospace; }
  :deep(pre) { background-color: var(--el-fill-color-dark); padding: 12px; border-radius: 8px; overflow-x: auto; }
}

.chat-input-area {
  padding: 20px;
  border-top: 1px solid var(--el-border-color);
  background-color: var(--el-bg-color);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  
  .el-input { flex: 1; }
}

.input-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
