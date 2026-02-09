<template>
  <div class="daily-analysis-container">
    <div class="daily-layout">
      <!-- Left: Stock Selection Panel -->
      <div class="stock-selection-panel">
        <el-card class="selection-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>自選股票</span>
              <el-button size="small" @click="refresh ConfigStocks">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          
          <div class="stock-list">
            <el-checkbox-group v-model="selectedStocks">
              <div 
                v-for="stock in availableStocks" 
                :key="stock.code"
                class="stock-item"
              >
                <el-checkbox :label="stock.code">
                  <div class="stock-item-content">
                    <span class="stock-name">{{ stock.name }}</span>
                    <span class="stock-code">{{ stock.code }}</span>
                  </div>
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </div>

          <div class="action-buttons">
            <el-button
              type="primary"
              :loading="isAnalyzing"
              :disabled="selectedStocks.length === 0"
              @click="analyzeStocks"
              block
            >
              <el-icon><TrendCharts /></el-icon>
              分析選中股票 ({{ selectedStocks.length }})
            </el-button>
            
            <el-button
              :loading="isReviewing"
              @click="marketReview"
              block
            >
              <el-icon><DataAnalysis /></el-icon>
              大盤複盤
            </el-button>
          </div>

          <el-divider />

          <div class="config-section">
            <el-form label-position="left" label-width="100px" size="small">
              <el-form-item label="報告類型">
                <el-radio-group v-model="reportType" size="small">
                  <el-radio label="simple">精簡</el-radio>
                  <el-radio label="full">完整</el-radio>
                </el-radio-group>
              </el-form-item>
              
              <el-form-item label="推送通知">
                <el-switch v-model="sendNotification" />
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </div>

      <!-- Center: Analysis Results -->
      <div class="analysis-results-panel">
        <el-card class="results-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>分析結果</span>
              <el-tag v-if="lastAnalysisTime" size="small" type="info">
                {{ lastAnalysisTime }}
              </el-tag>
            </div>
          </template>

          <div v-if="analysisResults.length === 0" class="no-results">
            <el-empty description="尚無分析結果" :image-size="80" />
          </div>

          <div v-else class="results-list">
            <div 
              v-for="result in analysisResults" 
              :key="result.code"
              class="result-item"
            >
              <el-card class="stock-result-card" shadow="hover">
                <div class="stock-header">
                  <h3 class="stock-title">
                    {{ result.name }} ({{ result.code }})
                  </h3>
                  <el-tag 
                    :type="getOperationTagType(result.operation_advice)"
                    size="large"
                  >
                    {{ result.operation_advice }}
                  </el-tag>
                </div>

                <div class="decision-dashboard">
                  <div class="core-conclusion">
                    <el-icon class="conclusion-icon"><Document /></el-icon>
                    <p>{{ result.core_conclusion || '綜合分析中...' }}</p>
                  </div>

                  <div v-if="result.buy_price" class="price-points">
                    <div class="price-item buy">
                      <label>狙擊買入</label>
                      <span>{{ result.buy_price }}</span>
                    </div>
                    <div class="price-item stop">
                      <label>止損價</label>
                      <span>{{ result.stop_loss }}</span>
                    </div>
                    <div class="price-item target">
                      <label>目標價</label>
                      <span>{{ result.target_price }}</span>
                    </div>
                  </div>

                  <div class="checklist" v-if="result.checklist">
                    <div 
                      v-for="(item, index) in parseChecklist(result.checklist)" 
                      :key="index"
                      class="checklist-item"
                      :class="item.status"
                    >
                      <el-icon v-if="item.status === 'pass'"><Check /></el-icon>
                      <el-icon v-else-if="item.status === 'warning'"><Warning /></el-icon>
                      <el-icon v-else><Close /></el-icon>
                      <span>{{ item.text }}</span>
                    </div>
                  </div>

                  <div class="sentiment-score">
                    <el-progress
                      :percentage="result.sentiment_score || 0"
                      :color="getSentimentColor(result.sentiment_score)"
                      :stroke-width="12"
                    />
                    <span class="score-label">綜合評分</span>
                  </div>
                </div>
              </el-card>
            </div>
          </div>

          <!-- Market Review Result -->
          <div v-if="marketReviewResult" class="market-review">
            <el-card class="review-card">
              <template #header>
                <div class="card-header">
                  <span>大盤複盤</span>
                </div>
              </template>
              <div class="review-content" v-html="marketReviewResult"></div>
            </el-card>
          </div>
        </el-card>
      </div>

      <!-- Right: History & Config -->
      <div class="right-panel">
        <el-card class="history-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>分析歷史</span>
              <el-button size="small" @click="loadHistory">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>

          <div v-if="analysisHistory.length === 0" class="no-history">
            <el-empty description="暫無歷史記錄" :image-size="60" />
          </div>

          <el-timeline v-else>
            <el-timeline-item
              v-for="(item, index) in analysisHistory"
              :key="index"
              :timestamp="item.created_at"
              placement="top"
            >
              <el-text>{{ item.stock_name }} ({{ item.stock_code }})</el-text>
              <br>
              <el-tag size="small" :type="getOperationTagType(item.operation_advice)">
                {{ item.operation_advice }}
              </el-tag>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <el-card class="config-info-card" shadow="never" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>系統配置</span>
            </div>
          </template>

          <div v-if="systemConfig" class="config-details">
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="即時行情">
                <el-tag v-if="systemConfig.enable_realtime_quote" type="success" size="small">啟用</el-tag>
                <el-tag v-else type="info" size="small">停用</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="籌碼分佈">
                <el-tag v-if="systemConfig.enable_chip_distribution" type="success" size="small">啟用</el-tag>
                <el-tag v-else type="info" size="small">停用</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="最大併發">
                {{ systemConfig.max_workers }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { 
  Refresh, 
  TrendCharts, 
  DataAnalysis, 
  Document, 
  Check, 
  Warning, 
  Close 
} from '@element-plus/icons-vue'
import axios from 'axios'

interface StockInfo {
  code: string
  name: string
}

interface AnalysisResult {
  code: string
  name: string
  operation_advice: string
  sentiment_score: number
  core_conclusion?: string
  buy_price?: number
  stop_loss?: number
  target_price?: number
  checklist?: string
}

const selectedStocks = ref<string[]>([])
const availableStocks = ref<StockInfo[]>([])
const analysisResults = ref<AnalysisResult[]>([])
const analysisHistory = ref<any[]>([])
const systemConfig = ref<any>(null)
const marketReviewResult = ref<string>('')

const isAnalyzing = ref(false)
const isReviewing = ref(false)
const reportType = ref('simple')
const sendNotification = ref(false)
const lastAnalysisTime = ref('')

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

// Load config stocks
const refreshConfigStocks = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/daily/config`)
    if (response.data.success) {
      systemConfig.value = response.data.config
      const stockList = response.data.config.stock_list || []
      
      // Convert stock codes to StockInfo objects
      availableStocks.value = stockList.map((code: string) => ({
        code,
        name: code // Will be updated after analysis
      }))
      
      ElMessage.success('配置載入成功')
    }
  } catch (error: any) {
    console.error('Failed to load config:', error)
    ElMessage.error(error.response?.data?.detail || '載入配置失敗')
  }
}

// Analyze stocks
const analyzeStocks = async () => {
  if (selectedStocks.value.length === 0) {
    ElMessage.warning('請先選擇要分析的股票')
    return
  }

  isAnalyzing.value = true
  
  try {
    const response = await axios.post(`${API_BASE}/api/daily/analyze`, {
      stock_codes: selectedStocks.value,
      full_report: reportType.value === 'full',
      send_notification: sendNotification.value,
      dry_run: false
    })

    if (response.data.success) {
      analysisResults.value = response.data.results
      lastAnalysisTime.value = new Date().toLocaleString('zh-TW')
      
      ElNotification({
        title: '分析完成',
        message: `成功分析 ${response.data.count} 隻股票`,
        type: 'success'
      })

      // Refresh history
      loadHistory()
    }
  } catch (error: any) {
    console.error('Analysis failed:', error)
    ElNotification({
      title: '分析失敗',
      message: error.response?.data?.detail || '請檢查後端服務',
      type: 'error'
    })
  } finally {
    isAnalyzing.value = false
  }
}

// Market review
const marketReview = async () => {
  isReviewing.value = true
  
  try {
    const response = await axios.post(`${API_BASE}/api/daily/market-review`, {
      send_notification: sendNotification.value
    })

    if (response.data.success) {
      marketReviewResult.value = response.data.report
      
      ElNotification({
        title: '大盤複盤完成',
        type: 'success'
      })
    }
  } catch (error: any) {
    console.error('Market review failed:', error)
    ElNotification({
      title: '複盤失敗',
      message: error.response?.data?.detail || '請檢查後端服務',
      type: 'error'
    })
  } finally {
    isReviewing.value = false
  }
}

// Load analysis history
const loadHistory = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/daily/history?limit=20`)
    if (response.data.success) {
      analysisHistory.value = response.data.history
    }
  } catch (error) {
    console.error('Failed to load history:', error)
  }
}

// Helper functions
const getOperationTagType = (advice: string) => {
  if (advice?.includes('買入') || advice?.includes('BUY')) return 'success'
  if (advice?.includes('賣出') || advice?.includes('SELL')) return 'danger'
  if (advice?.includes('觀望') || advice?.includes('HOLD')) return 'warning'
  return 'info'
}

const getSentimentColor = (score: number) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#409eff'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}

const parseChecklist = (checklist: string) => {
  if (!checklist) return []
  
  const items = checklist.split('\n').filter(line => line.trim())
  return items.map(item => {
    if (item.includes('✅')) return { text: item.replace('✅', '').trim(), status: 'pass' }
    if (item.includes('⚠️')) return { text: item.replace('⚠️', '').trim(), status: 'warning' }
    if (item.includes('❌')) return { text: item.replace('❌', '').trim(), status: 'fail' }
    return { text: item, status: 'unknown' }
  })
}

onMounted(() => {
  refreshConfigStocks()
  loadHistory()
})
</script>

<style scoped lang="scss">
.daily-analysis-container {
  width: 100%;
  height: calc(100vh - 60px);
  overflow: hidden;
  background-color: var(--el-bg-color-page);
}

.daily-layout {
  display: grid;
  grid-template-columns: 320px 1fr 360px;
  gap: 16px;
  height: 100%;
  padding: 16px;
}

// Stock Selection Panel
.stock-selection-panel {
  overflow-y: auto;
  
  .selection-card {
    height: 100%;
  }
  
  .stock-list {
    max-height: 400px;
    overflow-y: auto;
    margin-bottom: 16px;
  }
  
  .stock-item {
    padding: 8px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
    
    &:last-child {
      border-bottom: none;
    }
  }
  
  .stock-item-content {
    display: flex;
    flex-direction: column;
    gap: 4px;
    
    .stock-name {
      font-weight: 500;
    }
    
    .stock-code {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
  
  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .config-section {
    margin-top: 16px;
  }
}

// Analysis Results Panel
.analysis-results-panel {
  overflow-y: auto;
  
  .results-card {
    height: 100%;
  }
  
  .no-results {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 300px;
  }
  
  .results-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .stock-result-card {
    .stock-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      
      .stock-title {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
      }
    }
    
    .decision-dashboard {
      .core-conclusion {
        display: flex;
        gap: 12px;
        padding: 16px;
        background-color: var(--el-fill-color-light);
        border-radius: 8px;
        margin-bottom: 16px;
        
        .conclusion-icon {
          font-size: 24px;
          color: var(--el-color-primary);
        }
        
        p {
          margin: 0;
          line-height: 1.6;
        }
      }
      
      .price-points {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 16px;
        
        .price-item {
          padding: 12px;
          border-radius: 6px;
          text-align: center;
          
          label {
            display: block;
            font-size: 12px;
            color: var(--el-text-color-secondary);
            margin-bottom: 8px;
          }
          
          span {
            font-size: 20px;
            font-weight: 600;
          }
          
          &.buy {
            background-color: #f0f9ff;
            color: var(--el-color-primary);
          }
          
          &.stop {
            background-color: #fef0f0;
            color: var(--el-color-danger);
          }
          
          &.target {
            background-color: #f0f9ff;
            color: var(--el-color-success);
          }
        }
      }
      
      .checklist {
        margin-bottom: 16px;
        
        .checklist-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px;
          margin-bottom: 4px;
          border-radius: 4px;
          
          &.pass {
            color: var(--el-color-success);
            background-color: #f0f9ff;
          }
          
          &.warning {
            color: var(--el-color-warning);
            background-color: #fdf6ec;
          }
          
          &.fail {
            color: var(--el-color-danger);
            background-color: #fef0f0;
          }
        }
      }
      
      .sentiment-score {
        .score-label {
          display: block;
          text-align: center;
          margin-top: 8px;
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }
    }
  }
  
  .market-review {
    margin-top: 16px;
    
    .review-content {
      white-space: pre-wrap;
      line-height: 1.8;
    }
  }
}

// Right Panel
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  
  .history-card {
    flex: 1;
    max-height: 50%;
  }
  
  .config-info-card {
    flex-shrink: 0;
  }
  
  .no-history {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 150px;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  span {
    font-weight: 600;
    font-size: 16px;
  }
}
</style>
