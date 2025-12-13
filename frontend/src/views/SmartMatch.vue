<template>
  <div class="smart-match">
    <!-- Hero Section 搜索区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="hero-header">
          <div>
            <h1 class="hero-title">成果需求智能匹配</h1>
            <p class="hero-subtitle">输入您的技术难题或成果描述，AI 将为您智能匹配最合适的合作伙伴</p>
          </div>
          <el-button 
            type="primary" 
            size="large"
            @click="showAllHistoryDialog = true; loadAllImplementationPathHistory()"
            style="margin-left: 20px; flex-shrink: 0"
          >
            <el-icon><Clock /></el-icon>
            查看所有历史方案
          </el-button>
        </div>

        <div class="search-container">
          <el-input
            v-model="searchText"
            type="textarea"
            :rows="6"
            placeholder="请输入您的技术难题或成果描述..."
            class="search-textarea"
            :disabled="loading"
            :maxlength="1000"
            show-word-limit
          />

          <div class="mode-selector">
            <el-radio-group v-model="matchMode" size="large">
              <el-radio-button label="enterprise">我是企业找成果</el-radio-button>
              <el-radio-button label="researcher">我是专家找需求</el-radio-button>
            </el-radio-group>
          </div>

          <el-button
            type="primary"
            size="large"
            class="match-button"
            :loading="loading"
            @click="startMatch"
          >
            <el-icon v-if="!loading"><Search /></el-icon>
            <span>{{ loading ? '匹配中...' : '开始智能匹配' }}</span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 匹配结果区域 -->
    <div class="results-section" v-if="showResults">
      <div class="container">
        <div class="results-header">
          <div>
            <h2 class="results-title">匹配结果</h2>
            <p class="results-subtitle">为您找到 {{ filteredResults.length }} 个匹配项</p>
          </div>
          <div class="action-buttons" v-if="selectedPapers.length > 0">
            <el-button 
              type="success" 
              size="large"
              :loading="currentTask.status === 'generating' && !currentTask.taskId"
              :disabled="loading || currentTask.status === 'generating'"
              @click="startNewTask"
            >
              <el-icon><Document /></el-icon>
              生成实现路径 (已选 {{ selectedPapers.length }} 篇)
            </el-button>
            <!-- 只在生成中时显示查看进度按钮 -->
            <el-button 
              v-if="currentTask.status === 'generating'"
              type="primary" 
              size="large"
              :disabled="loading"
              @click="viewCurrentTask"
            >
              <el-icon><View /></el-icon>
              查看生成进度
            </el-button>
            <el-button @click="clearSelection" size="large">
              清空选择
            </el-button>
          </div>
          <div class="action-buttons" v-if="currentHistoryId">
            <el-button 
              type="info" 
              size="large"
              @click="showHistoryDialog = true; loadImplementationPathHistory()"
            >
              <el-icon><Clock /></el-icon>
              查看历史方案
            </el-button>
          </div>
        </div>

        <el-row :gutter="24">
          <el-col :xs="24" :sm="12" :md="8" v-for="item in filteredResults" :key="item.id">
            <div class="result-card-wrapper">
              <div class="paper-card" :class="{ 'selected': item.type === '论文' && isPaperSelected(item.paper_id) }">
                <div class="card-checkbox-wrapper" v-if="item.type === '论文' && item.paper_id">
                  <el-checkbox 
                    v-model="selectedPaperIds" 
                    :value="item.paper_id"
                    @change="handlePaperSelection(item.paper_id, $event)"
                    class="paper-checkbox"
                    size="large"
                  />
                </div>
              <div class="card-content">
                <div class="card-header">
                  <h3 class="paper-title">{{ item.title }}</h3>
                </div>
                <div class="card-body">
                  <div class="summary-content" v-html="highlightKeywords(item.summary)"></div>
                  
                  <!-- 推荐理由 -->
                  <div class="reason-section" v-if="item.reason">
                    <div class="reason-label">
                      <el-icon><Opportunity /></el-icon>
                      推荐理由
                    </div>
                    <div class="reason-text">{{ item.reason }}</div>
                  </div>
                  
                  <div class="confidence-section">
                    <div class="score-header">
                      <span class="score-label">匹配度</span>
                      <el-tag v-if="item.match_type" :type="getMatchTypeTagType(item.match_type)" size="small" effect="dark">
                        {{ item.match_type }}
                      </el-tag>
                    </div>
                    <el-progress
                      :percentage="item.matchScore"
                      :color="getScoreColor(item.matchScore)"
                      :stroke-width="8"
                      :show-text="true"
                      :format="(percentage) => `${percentage}%`"
                    />
                  </div>
                  
                  <div class="card-meta">
                    <el-tag v-if="item.type" :type="item.type === '成果' ? 'success' : 'primary'" size="small" effect="plain">
                      {{ item.type }}
                    </el-tag>
                    <span class="meta-item" v-if="item.field">
                      <el-icon><FolderOpened /></el-icon>
                      {{ item.field }}
                    </span>
                    <!-- 成果显示联系方式，论文显示作者 -->
                    <span class="meta-item" v-if="item.type === '成果' && item.contact_name">
                      <el-icon><User /></el-icon>
                      联系人: {{ item.contact_name }}
                    </span>
                    <span class="meta-item" v-else-if="item.type === '论文' && item.authors">
                      <el-icon><User /></el-icon>
                      {{ item.authors.split(',').slice(0, 2).join(',') }}{{ item.authors.split(',').length > 2 ? '等' : '' }}
                    </span>
                    <span class="meta-item" v-if="item.published_date">
                      <el-icon><Calendar /></el-icon>
                      {{ formatDate(item.published_date) }}
                    </span>
                  </div>
                </div>
                <div class="card-footer">
                  <el-button type="primary" size="default" @click="viewProposal(item.id)" plain>
                    <el-icon><Document /></el-icon>
                    查看详情
                  </el-button>
                  <!-- 只有论文有PDF，成果显示联系方式 -->
                  <el-button v-if="item.type === '论文' && item.pdf_url" @click="openPdf(item.pdf_url)" link type="primary">
                    <el-icon><Document /></el-icon>
                    查看PDF
                  </el-button>
                  <el-button v-if="item.type === '成果' && item.contact_phone" @click="copyContact(item)" link type="primary">
                    <el-icon><User /></el-icon>
                    复制联系方式
                  </el-button>
                </div>
              </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 实现路径对话框 -->
    <el-dialog
      v-model="showPathDialog"
      :title="dialogMode === 'generating' ? '生成实现路径中...' : dialogMode === 'result' ? '实现路径生成结果' : dialogMode === 'history' ? '历史实现路径方案' : '科研成果实现路径'"
      width="80%"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      class="implementation-path-dialog"
      @close="handlePathDialogClose"
    >
      <!-- 实时进度：仅在任务运行中显示，且不是查看历史方案时 -->
      <div class="path-section" v-if="dialogMode === 'generating' && currentTask.progress && currentTask.progress.status === 'running'">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <h3 style="margin: 0;">⏱ 当前进度</h3>
          <el-button 
            type="danger" 
            size="small"
            @click="cancelImplementationPath"
            :loading="cancellingPath"
          >
            <el-icon><Close /></el-icon>
            取消生成
          </el-button>
        </div>
        <p>
          <strong>状态：</strong>
          <span v-if="currentTask.progress.status === 'running'">生成中...</span>
          <span v-else-if="currentTask.progress.status === 'finished'">已完成</span>
          <span v-else-if="currentTask.progress.status === 'error'">出错</span>
          <span v-else-if="currentTask.progress.status === 'cancelled'">已取消</span>
          <span v-else>未知</span>
        </p>
        <p v-if="currentTask.progress.current_step">
          <strong>当前步骤：</strong>{{ currentTask.progress.current_step }}
        </p>
        <el-progress
          v-if="currentTask.progress.total_papers"
          :percentage="Math.round((currentTask.progress.completed_papers / currentTask.progress.total_papers) * 100)"
          :stroke-width="8"
          style="max-width: 400px; margin-top: 8px"
        />
      </div>

      <div v-if="dialogMode === 'generating' && currentTask.status === 'generating' && !currentTask.progress" class="path-loading">
        <el-skeleton :rows="10" animated />
      </div>
      <!-- 查看历史方案 -->
      <div v-else-if="dialogMode === 'history' && viewingHistoryItem" class="path-content">
        <!-- 耗时总览 -->
        <div class="path-section" v-if="viewingHistoryItem.timings">
          <h3>⏱ 性能概览</h3>
          <p v-if="viewingHistoryItem.timings.total_ms">
            <strong>总耗时：</strong>{{ (viewingHistoryItem.timings.total_ms / 1000).toFixed(2) }} 秒
          </p>
          <p v-if="viewingHistoryItem.timings.implementation_path_ms">
            <strong>实现路径汇总耗时：</strong>{{ (viewingHistoryItem.timings.implementation_path_ms / 1000).toFixed(2) }} 秒
          </p>
          <div v-if="viewingHistoryItem.timings.per_paper && viewingHistoryItem.timings.per_paper.length" style="margin-top: 10px">
            <strong>单篇论文耗时：</strong>
            <el-table
              :data="viewingHistoryItem.timings.per_paper"
              size="small"
              style="width: 100%; margin-top: 8px"
            >
              <el-table-column prop="title" label="论文" min-width="220" />
              <el-table-column
                label="PDF解析 (ms)"
                min-width="120"
              >
                <template #default="scope">
                  {{ scope.row.timings?.pdf_ms ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column
                label="LLM精读 (ms)"
                min-width="120"
              >
                <template #default="scope">
                  {{ scope.row.timings?.llm_ms ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column
                label="合计 (ms)"
                min-width="120"
              >
                <template #default="scope">
                  {{ scope.row.timings?.total_ms ?? '-' }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 架构决策 -->
        <div class="path-section" v-if="viewingHistoryItem.implementation_path?.architectural_decision">
          <h3>🧠 架构决策</h3>
          <p v-if="viewingHistoryItem.implementation_path.architectural_decision.selected_methodology">
            <strong>选定方法：</strong>
            {{ viewingHistoryItem.implementation_path.architectural_decision.selected_methodology }}
          </p>
          <p v-if="viewingHistoryItem.implementation_path.architectural_decision.tradeoff_reasoning">
            <strong>权衡分析：</strong>
            {{ viewingHistoryItem.implementation_path.architectural_decision.tradeoff_reasoning }}
          </p>
          <p v-else-if="viewingHistoryItem.implementation_path.architectural_decision.reasoning">
            <strong>决策说明：</strong>
            {{ viewingHistoryItem.implementation_path.architectural_decision.reasoning }}
          </p>
          <p v-if="viewingHistoryItem.implementation_path.architectural_decision.discarded_methodologies">
            <strong>未采用方案：</strong>
            {{ viewingHistoryItem.implementation_path.architectural_decision.discarded_methodologies }}
          </p>
        </div>

        <!-- 整体概述 -->
        <div class="path-section" v-if="viewingHistoryItem.implementation_path?.overview">
          <h3>📋 整体概述</h3>
          <p style="white-space: pre-line">{{ viewingHistoryItem.implementation_path.overview }}</p>
        </div>

        <!-- 技术选型 -->
        <div class="path-section" v-if="viewingHistoryItem.implementation_path?.technology_selection">
          <h3>🔧 技术选型</h3>
          <div class="tech-selection">
            <div v-if="viewingHistoryItem.implementation_path.technology_selection.primary_techniques">
              <strong>主要技术栈：</strong>
              <el-tag 
                v-for="tech in viewingHistoryItem.implementation_path.technology_selection.primary_techniques" 
                :key="tech"
                type="success"
                style="margin: 5px"
              >
                {{ tech }}
              </el-tag>
            </div>
            <p v-if="viewingHistoryItem.implementation_path.technology_selection.integration_strategy" style="margin-top: 10px">
              <strong>核心方案：</strong>{{ viewingHistoryItem.implementation_path.technology_selection.integration_strategy }}
            </p>
          </div>
        </div>

        <!-- 实施阶段 -->
        <div class="path-section" v-if="viewingHistoryItem.implementation_path?.implementation_phases">
          <h3>📅 实施阶段</h3>
          <el-timeline>
            <el-timeline-item
              v-for="phase in viewingHistoryItem.implementation_path.implementation_phases"
              :key="phase.phase"
              :timestamp="phase.estimated_time"
              placement="top"
            >
              <el-card>
                <h4>{{ phase.name }}</h4>
                <div v-if="phase.requirement_alignment" style="margin-bottom: 15px; padding: 10px; background: #e6f7ff; border-left: 3px solid #1890ff; border-radius: 4px">
                  <strong>🎯 需求对齐：</strong>
                  <p style="margin: 5px 0 0 0">{{ phase.requirement_alignment }}</p>
                </div>
                <div v-if="phase.user_value" style="margin-bottom: 15px; padding: 10px; background: #f6ffed; border-left: 3px solid #52c41a; border-radius: 4px">
                  <strong>💎 用户价值：</strong>
                  <p style="margin: 5px 0 0 0">{{ phase.user_value }}</p>
                </div>
                <div v-if="phase.objectives && phase.objectives.length" class="phase-objectives">
                  <div class="phase-section-title">🎯 目标</div>
                  <div class="phase-objectives-tags">
                    <el-tag
                      v-for="(obj, idx) in phase.objectives"
                      :key="obj + idx"
                      effect="light"
                      type="info"
                      class="phase-pill-tag"
                    >
                      {{ idx + 1 }}. {{ obj }}
                    </el-tag>
                  </div>
                </div>
                <div v-if="phase.deliverables" style="margin-top: 10px">
                  <strong>交付物：</strong>
                  <ul>
                    <li v-for="del in phase.deliverables" :key="del">{{ del }}</li>
                  </ul>
                </div>
                <div v-if="phase.key_tasks && phase.key_tasks.length" class="phase-key-tasks">
                  <div class="phase-section-title">🛠 关键任务</div>
                  <ul class="phase-task-list">
                    <li
                      v-for="(task, idx) in phase.key_tasks"
                      :key="task + idx"
                      class="phase-task-item"
                    >
                      <span class="phase-task-index">{{ idx + 1 }}</span>
                      <span class="phase-task-text">{{ task }}</span>
                    </li>
                  </ul>
                </div>
                <div v-if="phase.definition_of_done" style="margin-top: 15px; padding: 10px; background: #fff7e6; border-left: 3px solid #faad14; border-radius: 4px">
                  <strong>✅ 验收标准：</strong>
                  <p style="margin: 5px 0 0 0">{{ phase.definition_of_done }}</p>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>

        <!-- 风险评估 -->
        <div class="path-section" v-if="viewingHistoryItem.implementation_path?.risk_assessment">
          <h3>⚠️ 风险评估</h3>
          <div class="risk-assessment">
            <div v-if="viewingHistoryItem.implementation_path.risk_assessment.technical_risks">
              <strong>技术风险：</strong>
              <ul>
                <li v-for="risk in viewingHistoryItem.implementation_path.risk_assessment.technical_risks" :key="risk">{{ risk }}</li>
              </ul>
            </div>
            <div v-if="viewingHistoryItem.implementation_path.risk_assessment.mitigation_strategies" style="margin-top: 10px">
              <strong>应对策略：</strong>
              <ul>
                <li v-for="strategy in viewingHistoryItem.implementation_path.risk_assessment.mitigation_strategies" :key="strategy">{{ strategy }}</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 成功标准 -->
        <div class="path-section" v-if="viewingHistoryItem.implementation_path?.success_criteria">
          <h3>✅ 成功标准</h3>
          <ul>
            <li v-for="criteria in viewingHistoryItem.implementation_path.success_criteria" :key="criteria">{{ criteria }}</li>
          </ul>
        </div>

        <!-- 论文分析详情 -->
        <div class="path-section" v-if="viewingHistoryItem.papers_analysis && viewingHistoryItem.papers_analysis.length > 0">
          <h3>📄 论文分析详情</h3>
          <el-collapse>
            <el-collapse-item
              v-for="(paper, index) in viewingHistoryItem.papers_analysis"
              :key="index"
              :title="paper.title"
            >
              <div v-if="paper.status === 'success' && paper.analysis">
                <template v-if="paper.analysis.analysis">
                  <div class="paper-analysis-content">
                    <el-tag v-if="paper.analysis.paper_type" type="info" style="margin-bottom: 15px">
                      论文类型：{{ paper.analysis.paper_type }}
                    </el-tag>
                    <div v-if="paper.analysis.analysis.big_idea" class="analysis-item">
                      <h4>💡 核心创新点</h4>
                      <p>{{ paper.analysis.analysis.big_idea }}</p>
                    </div>
                    <div v-if="paper.analysis.analysis.engineering_analysis" class="analysis-item">
                      <h4>🔧 工程分析</h4>
                      <div v-if="paper.analysis.analysis.engineering_analysis.model_architecture">
                        <strong>模型架构：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.model_architecture }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.input_spec" style="margin-top: 10px">
                        <strong>输入规格：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.input_spec }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.output_spec" style="margin-top: 10px">
                        <strong>输出规格：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.output_spec }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.loss_function" style="margin-top: 10px">
                        <strong>损失函数：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.loss_function }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.key_hyperparameters && paper.analysis.analysis.engineering_analysis.key_hyperparameters.length > 0" style="margin-top: 10px">
                        <strong>关键超参数：</strong>
                        <el-tag 
                          v-for="(param, idx) in paper.analysis.analysis.engineering_analysis.key_hyperparameters" 
                          :key="idx"
                          style="margin: 3px"
                        >
                          {{ param }}
                        </el-tag>
                      </div>
                    </div>
                    <div v-if="paper.analysis.analysis.training_procedure" class="analysis-item">
                      <h4>📚 训练流程</h4>
                      <div v-if="paper.analysis.analysis.training_procedure.data_processing">
                        <strong>数据处理：</strong>
                        <p>{{ paper.analysis.analysis.training_procedure.data_processing }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.training_procedure.optimization" style="margin-top: 10px">
                        <strong>优化策略：</strong>
                        <p>{{ paper.analysis.analysis.training_procedure.optimization }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.training_procedure.regularization_tricks && paper.analysis.analysis.training_procedure.regularization_tricks.length > 0" style="margin-top: 10px">
                        <strong>正则化技巧：</strong>
                        <ul>
                          <li v-for="(trick, idx) in paper.analysis.analysis.training_procedure.regularization_tricks" :key="idx">
                            {{ trick }}
                          </li>
                        </ul>
                      </div>
                    </div>
                    <div v-if="paper.analysis.analysis.inference_strategy" class="analysis-item">
                      <h4>⚡ 推理策略</h4>
                      <div v-if="paper.analysis.analysis.inference_strategy.sampling_method">
                        <strong>采样方法：</strong>
                        <p>{{ paper.analysis.analysis.inference_strategy.sampling_method }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.inference_strategy.latency_estimation" style="margin-top: 10px">
                        <strong>延迟估算：</strong>
                        <p>{{ paper.analysis.analysis.inference_strategy.latency_estimation }}</p>
                      </div>
                    </div>
                    <div v-if="paper.analysis.analysis.reproducibility" class="analysis-item">
                      <h4>🔬 可复现性</h4>
                      <div v-if="paper.analysis.analysis.reproducibility.implementation_gap">
                        <strong>实现难点：</strong>
                        <p>{{ paper.analysis.analysis.reproducibility.implementation_gap }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.reproducibility.reproducibility_score" style="margin-top: 10px">
                        <strong>可复现性评分：</strong>
                        <el-rate 
                          :model-value="parseInt(paper.analysis.analysis.reproducibility.reproducibility_score)" 
                          disabled 
                          show-score
                          text-color="#ff9900"
                          score-template="{value}"
                        />
                      </div>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div v-if="paper.analysis.core_techniques">
                    <strong>核心技术：</strong>
                    <el-tag 
                      v-for="tech in paper.analysis.core_techniques" 
                      :key="tech"
                      style="margin: 3px"
                    >
                      {{ tech }}
                    </el-tag>
                  </div>
                  <p v-if="paper.analysis.summary" style="margin-top: 10px">
                    <strong>总结：</strong>{{ paper.analysis.summary }}
                  </p>
                  <p v-if="paper.analysis.key_implementation_details" style="margin-top: 10px">
                    <strong>实现细节：</strong>{{ paper.analysis.key_implementation_details }}
                  </p>
                </template>
              </div>
              <div v-else>
                <el-alert :title="paper.error_message || '分析失败'" type="error" />
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      <!-- 查看当前任务结果 -->
      <div v-else-if="dialogMode === 'result' && currentTask.result" class="path-content">
        <!-- 耗时总览 -->
        <div class="path-section" v-if="pathTimings">
          <h3>⏱ 性能概览</h3>
          <p v-if="pathTimings.total_ms">
            <strong>总耗时：</strong>{{ (pathTimings.total_ms / 1000).toFixed(2) }} 秒
          </p>
          <p v-if="pathTimings.implementation_path_ms">
            <strong>实现路径汇总耗时：</strong>{{ (pathTimings.implementation_path_ms / 1000).toFixed(2) }} 秒
          </p>
          <div v-if="pathTimings.per_paper && pathTimings.per_paper.length" style="margin-top: 10px">
            <strong>单篇论文耗时：</strong>
            <el-table
              :data="pathTimings.per_paper"
              size="small"
              style="width: 100%; margin-top: 8px"
            >
              <el-table-column prop="title" label="论文" min-width="220" />
              <el-table-column
                label="PDF解析 (ms)"
                min-width="120"
              >
                <template #default="scope">
                  {{ scope.row.timings?.pdf_ms ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column
                label="LLM精读 (ms)"
                min-width="120"
              >
                <template #default="scope">
                  {{ scope.row.timings?.llm_ms ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column
                label="合计 (ms)"
                min-width="120"
              >
                <template #default="scope">
                  {{ scope.row.timings?.total_ms ?? '-' }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 架构决策（来自 LLM 的 architectural_decision） -->
        <div class="path-section" v-if="implementationPath.architectural_decision">
          <h3>🧠 架构决策</h3>
          <p v-if="implementationPath.architectural_decision.selected_methodology">
            <strong>选定方法：</strong>
            {{ implementationPath.architectural_decision.selected_methodology }}
          </p>
          <p v-if="implementationPath.architectural_decision.tradeoff_reasoning">
            <strong>权衡分析：</strong>
            {{ implementationPath.architectural_decision.tradeoff_reasoning }}
          </p>
          <p v-else-if="implementationPath.architectural_decision.reasoning">
            <strong>决策说明：</strong>
            {{ implementationPath.architectural_decision.reasoning }}
          </p>
          <p v-if="implementationPath.architectural_decision.discarded_methodologies">
            <strong>未采用方案：</strong>
            {{ implementationPath.architectural_decision.discarded_methodologies }}
          </p>
        </div>

        <!-- 整体概述（由后端根据决策 + pipeline 拼接） -->
        <div class="path-section" v-if="implementationPath.overview">
          <h3>📋 整体概述</h3>
          <p style="white-space: pre-line">{{ implementationPath.overview }}</p>
        </div>

        <!-- 技术选型（tech_stack + 选定 methodology） -->
        <div class="path-section" v-if="implementationPath.technology_selection">
          <h3>🔧 技术选型</h3>
          <div class="tech-selection">
            <div v-if="implementationPath.technology_selection.primary_techniques">
              <strong>主要技术栈：</strong>
              <el-tag 
                v-for="tech in implementationPath.technology_selection.primary_techniques" 
                :key="tech"
                type="success"
                style="margin: 5px"
              >
                {{ tech }}
              </el-tag>
            </div>
            <p v-if="implementationPath.technology_selection.integration_strategy" style="margin-top: 10px">
              <strong>核心方案：</strong>{{ implementationPath.technology_selection.integration_strategy }}
            </p>
          </div>
        </div>

        <!-- 实施阶段 -->
        <div class="path-section" v-if="implementationPath.implementation_phases">
          <h3>📅 实施阶段</h3>
          <el-timeline>
            <el-timeline-item
              v-for="phase in implementationPath.implementation_phases"
              :key="phase.phase"
              :timestamp="phase.estimated_time"
              placement="top"
            >
              <el-card>
                <h4>{{ phase.name }}</h4>
                
                <!-- 需求对齐：该阶段如何服务于用户需求 -->
                <div v-if="phase.requirement_alignment" style="margin-bottom: 15px; padding: 10px; background: #e6f7ff; border-left: 3px solid #1890ff; border-radius: 4px">
                  <strong>🎯 需求对齐：</strong>
                  <p style="margin: 5px 0 0 0">{{ phase.requirement_alignment }}</p>
                </div>

                <!-- 用户价值：该阶段完成后用户能获得什么价值 -->
                <div v-if="phase.user_value" style="margin-bottom: 15px; padding: 10px; background: #f6ffed; border-left: 3px solid #52c41a; border-radius: 4px">
                  <strong>💎 用户价值：</strong>
                  <p style="margin: 5px 0 0 0">{{ phase.user_value }}</p>
                </div>

                <!-- 阶段目标：改为标签样式 -->
                <div v-if="phase.objectives && phase.objectives.length" class="phase-objectives">
                  <div class="phase-section-title">🎯 目标</div>
                  <div class="phase-objectives-tags">
                    <el-tag
                      v-for="(obj, idx) in phase.objectives"
                      :key="obj + idx"
                      effect="light"
                      type="info"
                      class="phase-pill-tag"
                    >
                      {{ idx + 1 }}. {{ obj }}
                    </el-tag>
                  </div>
                </div>
                <div v-if="phase.deliverables" style="margin-top: 10px">
                  <strong>交付物：</strong>
                  <ul>
                    <li v-for="del in phase.deliverables" :key="del">{{ del }}</li>
                  </ul>
                </div>
                <!-- 关键任务：改为编号清单样式 -->
                <div v-if="phase.key_tasks && phase.key_tasks.length" class="phase-key-tasks">
                  <div class="phase-section-title">🛠 关键任务</div>
                  <ul class="phase-task-list">
                    <li
                      v-for="(task, idx) in phase.key_tasks"
                      :key="task + idx"
                      class="phase-task-item"
                    >
                      <span class="phase-task-index">{{ idx + 1 }}</span>
                      <span class="phase-task-text">{{ task }}</span>
                    </li>
                  </ul>
                </div>
                <div v-if="phase.definition_of_done" style="margin-top: 15px; padding: 10px; background: #fff7e6; border-left: 3px solid #faad14; border-radius: 4px">
                  <strong>✅ 验收标准：</strong>
                  <p style="margin: 5px 0 0 0">{{ phase.definition_of_done }}</p>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>

        <!-- 风险评估 -->
        <div class="path-section" v-if="implementationPath.risk_assessment">
          <h3>⚠️ 风险评估</h3>
          <div class="risk-assessment">
            <div v-if="implementationPath.risk_assessment.technical_risks">
              <strong>技术风险：</strong>
              <ul>
                <li v-for="risk in implementationPath.risk_assessment.technical_risks" :key="risk">{{ risk }}</li>
              </ul>
            </div>
            <div v-if="implementationPath.risk_assessment.mitigation_strategies" style="margin-top: 10px">
              <strong>应对策略：</strong>
              <ul>
                <li v-for="strategy in implementationPath.risk_assessment.mitigation_strategies" :key="strategy">{{ strategy }}</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 成功标准 -->
        <div class="path-section" v-if="implementationPath.success_criteria">
          <h3>✅ 成功标准</h3>
          <ul>
            <li v-for="criteria in implementationPath.success_criteria" :key="criteria">{{ criteria }}</li>
          </ul>
        </div>

        <!-- 论文分析详情 -->
        <div class="path-section" v-if="papersAnalysis && papersAnalysis.length > 0">
          <h3>📄 论文分析详情</h3>
          <el-collapse>
            <el-collapse-item
              v-for="(paper, index) in papersAnalysis"
              :key="index"
              :title="paper.title"
            >
              <div v-if="paper.status === 'success' && paper.analysis">
                <!-- 处理新的分析结果结构：paper.analysis 可能包含 paper_type 和 analysis 字段 -->
                <template v-if="paper.analysis.analysis">
                  <!-- 新格式：paper.analysis.analysis 包含实际的精读结果 -->
                  <div class="paper-analysis-content">
                    <el-tag v-if="paper.analysis.paper_type" type="info" style="margin-bottom: 15px">
                      论文类型：{{ paper.analysis.paper_type }}
                    </el-tag>
                    
                    <!-- 核心创新点 -->
                    <div v-if="paper.analysis.analysis.big_idea" class="analysis-item">
                      <h4>💡 核心创新点</h4>
                      <p>{{ paper.analysis.analysis.big_idea }}</p>
                    </div>

                    <!-- 工程分析 -->
                    <div v-if="paper.analysis.analysis.engineering_analysis" class="analysis-item">
                      <h4>🔧 工程分析</h4>
                      <div v-if="paper.analysis.analysis.engineering_analysis.model_architecture">
                        <strong>模型架构：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.model_architecture }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.input_spec" style="margin-top: 10px">
                        <strong>输入规格：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.input_spec }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.output_spec" style="margin-top: 10px">
                        <strong>输出规格：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.output_spec }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.loss_function" style="margin-top: 10px">
                        <strong>损失函数：</strong>
                        <p>{{ paper.analysis.analysis.engineering_analysis.loss_function }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.engineering_analysis.key_hyperparameters && paper.analysis.analysis.engineering_analysis.key_hyperparameters.length > 0" style="margin-top: 10px">
                        <strong>关键超参数：</strong>
                        <el-tag 
                          v-for="(param, idx) in paper.analysis.analysis.engineering_analysis.key_hyperparameters" 
                          :key="idx"
                          style="margin: 3px"
                        >
                          {{ param }}
                        </el-tag>
                      </div>
                    </div>

                    <!-- 训练流程 -->
                    <div v-if="paper.analysis.analysis.training_procedure" class="analysis-item">
                      <h4>📚 训练流程</h4>
                      <div v-if="paper.analysis.analysis.training_procedure.data_processing">
                        <strong>数据处理：</strong>
                        <p>{{ paper.analysis.analysis.training_procedure.data_processing }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.training_procedure.optimization" style="margin-top: 10px">
                        <strong>优化策略：</strong>
                        <p>{{ paper.analysis.analysis.training_procedure.optimization }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.training_procedure.regularization_tricks && paper.analysis.analysis.training_procedure.regularization_tricks.length > 0" style="margin-top: 10px">
                        <strong>正则化技巧：</strong>
                        <ul>
                          <li v-for="(trick, idx) in paper.analysis.analysis.training_procedure.regularization_tricks" :key="idx">
                            {{ trick }}
                          </li>
                        </ul>
                      </div>
                    </div>

                    <!-- 推理策略 -->
                    <div v-if="paper.analysis.analysis.inference_strategy" class="analysis-item">
                      <h4>⚡ 推理策略</h4>
                      <div v-if="paper.analysis.analysis.inference_strategy.sampling_method">
                        <strong>采样方法：</strong>
                        <p>{{ paper.analysis.analysis.inference_strategy.sampling_method }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.inference_strategy.latency_estimation" style="margin-top: 10px">
                        <strong>延迟估算：</strong>
                        <p>{{ paper.analysis.analysis.inference_strategy.latency_estimation }}</p>
                      </div>
                    </div>

                    <!-- 可复现性 -->
                    <div v-if="paper.analysis.analysis.reproducibility" class="analysis-item">
                      <h4>🔬 可复现性</h4>
                      <div v-if="paper.analysis.analysis.reproducibility.implementation_gap">
                        <strong>实现难点：</strong>
                        <p>{{ paper.analysis.analysis.reproducibility.implementation_gap }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.reproducibility.reproducibility_score" style="margin-top: 10px">
                        <strong>可复现性评分：</strong>
                        <el-rate 
                          :model-value="parseInt(paper.analysis.analysis.reproducibility.reproducibility_score)" 
                          disabled 
                          show-score
                          text-color="#ff9900"
                          score-template="{value}"
                        />
                      </div>
                    </div>

                    <!-- 系统类论文的特殊字段 -->
                    <div v-if="paper.analysis.analysis.system_components" class="analysis-item">
                      <h4>🏗️ 系统组件</h4>
                      <div v-if="paper.analysis.analysis.core_problem" style="margin-bottom: 15px">
                        <strong>核心问题：</strong>
                        <p>{{ paper.analysis.analysis.core_problem }}</p>
                      </div>
                      <div v-for="(component, idx) in paper.analysis.analysis.system_components" :key="idx" style="margin-top: 10px; padding: 10px; background: #f5f7fa; border-radius: 4px">
                        <strong>{{ component.name }}</strong>
                        <p><em>{{ component.responsibility }}</em></p>
                        <div v-if="component.inputs && component.inputs.length > 0" style="margin-top: 5px">
                          <strong>输入：</strong>{{ component.inputs.join(', ') }}
                        </div>
                        <div v-if="component.outputs && component.outputs.length > 0" style="margin-top: 5px">
                          <strong>输出：</strong>{{ component.outputs.join(', ') }}
                        </div>
                      </div>
                      <div v-if="paper.analysis.analysis.variation_modeling" style="margin-top: 15px">
                        <strong>变化建模：</strong>
                        <p>{{ paper.analysis.analysis.variation_modeling.feature_model_type }}</p>
                      </div>
                      <div v-if="paper.analysis.analysis.runtime_policies" style="margin-top: 15px">
                        <strong>运行时策略：</strong>
                        <p>{{ paper.analysis.analysis.runtime_policies.threshold_definitions }}</p>
                      </div>
                    </div>

                    <!-- 综述类论文 (Survey) -->
                    <div v-if="paper.analysis.analysis.taxonomy_tree" class="analysis-item">
                      <h4>📚 分类树</h4>
                      <div v-if="paper.analysis.analysis.taxonomy_tree.root">
                        <strong>领域：</strong>{{ paper.analysis.analysis.taxonomy_tree.root }}
                      </div>
                      <div v-if="paper.analysis.analysis.taxonomy_tree.children && paper.analysis.analysis.taxonomy_tree.children.length > 0" style="margin-top: 10px">
                        <strong>子类：</strong>
                        <ul>
                          <li v-for="(child, idx) in paper.analysis.analysis.taxonomy_tree.children" :key="idx">
                            <strong>{{ child.name }}</strong>
                            <span v-if="child.subtypes && child.subtypes.length > 0">
                              ({{ child.subtypes.join(', ') }})
                            </span>
                          </li>
                        </ul>
                      </div>
                    </div>

                    <div v-if="paper.analysis.analysis.comparison_matrix && paper.analysis.analysis.comparison_matrix.length > 0" class="analysis-item">
                      <h4>⚖️ 方法对比矩阵</h4>
                      <div v-for="(method, idx) in paper.analysis.analysis.comparison_matrix" :key="idx" style="margin-top: 10px; padding: 10px; background: #f5f7fa; border-radius: 4px">
                        <strong>{{ method.method_name }}</strong>
                        <div v-if="method.pros && method.pros.length > 0" style="margin-top: 5px">
                          <strong>优点：</strong>
                          <ul>
                            <li v-for="(pro, pidx) in method.pros" :key="pidx">{{ pro }}</li>
                          </ul>
                        </div>
                        <div v-if="method.cons && method.cons.length > 0" style="margin-top: 5px">
                          <strong>缺点：</strong>
                          <ul>
                            <li v-for="(con, cidx) in method.cons" :key="cidx">{{ con }}</li>
                          </ul>
                        </div>
                        <div v-if="method.best_scenario" style="margin-top: 5px">
                          <strong>适用场景：</strong>{{ method.best_scenario }}
                        </div>
                      </div>
                    </div>

                    <div v-if="paper.analysis.analysis.open_challenges && paper.analysis.analysis.open_challenges.length > 0" class="analysis-item">
                      <h4>🔮 开放挑战</h4>
                      <ul>
                        <li v-for="(challenge, idx) in paper.analysis.analysis.open_challenges" :key="idx">
                          {{ challenge }}
                        </li>
                      </ul>
                    </div>

                    <!-- 基准类论文 (Benchmark) -->
                    <div v-if="paper.analysis.analysis.dataset_stats" class="analysis-item">
                      <h4>📊 数据集统计</h4>
                      <div v-if="paper.analysis.analysis.dataset_stats.num_samples">
                        <strong>样本数量：</strong>{{ paper.analysis.analysis.dataset_stats.num_samples }}
                      </div>
                      <div v-if="paper.analysis.analysis.dataset_stats.languages && paper.analysis.analysis.dataset_stats.languages.length > 0" style="margin-top: 5px">
                        <strong>语言：</strong>{{ paper.analysis.analysis.dataset_stats.languages.join(', ') }}
                      </div>
                      <div v-if="paper.analysis.analysis.dataset_stats.domains && paper.analysis.analysis.dataset_stats.domains.length > 0" style="margin-top: 5px">
                        <strong>领域：</strong>{{ paper.analysis.analysis.dataset_stats.domains.join(', ') }}
                      </div>
                    </div>

                    <div v-if="paper.analysis.analysis.collection_pipeline" class="analysis-item">
                      <h4>🔄 数据收集流程</h4>
                      <div v-if="paper.analysis.analysis.collection_pipeline.sources && paper.analysis.analysis.collection_pipeline.sources.length > 0">
                        <strong>数据来源：</strong>{{ paper.analysis.analysis.collection_pipeline.sources.join(', ') }}
                      </div>
                      <div v-if="paper.analysis.analysis.collection_pipeline.filtering_rules && paper.analysis.analysis.collection_pipeline.filtering_rules.length > 0" style="margin-top: 10px">
                        <strong>过滤规则：</strong>
                        <ul>
                          <li v-for="(rule, idx) in paper.analysis.analysis.collection_pipeline.filtering_rules" :key="idx">{{ rule }}</li>
                        </ul>
                      </div>
                    </div>

                    <div v-if="paper.analysis.analysis.evaluation_protocol" class="analysis-item">
                      <h4>📈 评估协议</h4>
                      <div v-if="paper.analysis.analysis.evaluation_protocol.tasks && paper.analysis.analysis.evaluation_protocol.tasks.length > 0">
                        <strong>任务：</strong>{{ paper.analysis.analysis.evaluation_protocol.tasks.join(', ') }}
                      </div>
                      <div v-if="paper.analysis.analysis.evaluation_protocol.metrics && paper.analysis.analysis.evaluation_protocol.metrics.length > 0" style="margin-top: 10px">
                        <strong>指标：</strong>{{ paper.analysis.analysis.evaluation_protocol.metrics.join(', ') }}
                      </div>
                    </div>

                    <!-- 工业类论文 (Industry) -->
                    <div v-if="paper.analysis.analysis.deployment_scale" class="analysis-item">
                      <h4>🏭 部署规模</h4>
                      <div v-if="paper.analysis.analysis.deployment_scale.qps">
                        <strong>QPS：</strong>{{ paper.analysis.analysis.deployment_scale.qps }}
                      </div>
                      <div v-if="paper.analysis.analysis.deployment_scale.num_users" style="margin-top: 5px">
                        <strong>用户规模：</strong>{{ paper.analysis.analysis.deployment_scale.num_users }}
                      </div>
                    </div>

                    <div v-if="paper.analysis.analysis.lessons_learned && paper.analysis.analysis.lessons_learned.length > 0" class="analysis-item">
                      <h4>💡 经验教训</h4>
                      <ul>
                        <li v-for="(lesson, idx) in paper.analysis.analysis.lessons_learned" :key="idx">
                          {{ lesson }}
                        </li>
                      </ul>
                    </div>

                    <div v-if="paper.analysis.analysis.negative_results && paper.analysis.analysis.negative_results.length > 0" class="analysis-item">
                      <h4>❌ 失败案例</h4>
                      <ul>
                        <li v-for="(result, idx) in paper.analysis.analysis.negative_results" :key="idx">
                          {{ result }}
                        </li>
                      </ul>
                    </div>

                    <!-- 理论类论文 (Theory) -->
                    <div v-if="paper.analysis.analysis.core_theorems && paper.analysis.analysis.core_theorems.length > 0" class="analysis-item">
                      <h4>📐 核心定理</h4>
                      <div v-for="(theorem, idx) in paper.analysis.analysis.core_theorems" :key="idx" style="margin-top: 10px; padding: 10px; background: #f5f7fa; border-radius: 4px">
                        <strong>{{ theorem.name }}</strong>
                        <p v-if="theorem.informal_statement" style="margin-top: 5px">{{ theorem.informal_statement }}</p>
                        <div v-if="theorem.conditions && theorem.conditions.length > 0" style="margin-top: 5px">
                          <strong>关键假设：</strong>
                          <ul>
                            <li v-for="(condition, cidx) in theorem.conditions" :key="cidx">{{ condition }}</li>
                          </ul>
                        </div>
                        <div v-if="theorem.implications_for_practice" style="margin-top: 5px">
                          <strong>工程启示：</strong>{{ theorem.implications_for_practice }}
                        </div>
                      </div>
                    </div>

                    <!-- 如果没有任何匹配的字段，显示原始 JSON（调试用） -->
                    <div v-if="!paper.analysis.analysis.big_idea && !paper.analysis.analysis.system_components && !paper.analysis.analysis.taxonomy_tree && !paper.analysis.analysis.dataset_stats && !paper.analysis.analysis.deployment_scale && !paper.analysis.analysis.core_theorems" class="analysis-item">
                      <h4>📋 分析结果</h4>
                      <pre style="background: #f5f7fa; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px">{{ JSON.stringify(paper.analysis.analysis, null, 2) }}</pre>
                    </div>
                  </div>
                </template>
                
                <!-- 兼容旧格式：直接使用 paper.analysis -->
                <template v-else>
                  <div v-if="paper.analysis.core_techniques">
                    <strong>核心技术：</strong>
                    <el-tag 
                      v-for="tech in paper.analysis.core_techniques" 
                      :key="tech"
                      style="margin: 3px"
                    >
                      {{ tech }}
                    </el-tag>
                  </div>
                  <p v-if="paper.analysis.summary" style="margin-top: 10px">
                    <strong>总结：</strong>{{ paper.analysis.summary }}
                  </p>
                  <p v-if="paper.analysis.key_implementation_details" style="margin-top: 10px">
                    <strong>实现细节：</strong>{{ paper.analysis.key_implementation_details }}
                  </p>
                  <p v-if="paper.analysis.technical_advantages" style="margin-top: 10px">
                    <strong>技术优势：</strong>{{ paper.analysis.technical_advantages }}
                  </p>
                  <p v-if="paper.analysis.implementation_challenges" style="margin-top: 10px">
                    <strong>实现难点：</strong>{{ paper.analysis.implementation_challenges }}
                  </p>
                </template>
              </div>
              <div v-else>
                <el-alert :title="paper.error_message || '分析失败'" type="error" />
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      <div v-else-if="pathError" class="path-error">
        <el-alert :title="pathError" type="error" />
      </div>
      <template #footer>
        <el-button @click="showPathDialog = false">关闭</el-button>
        <!-- 历史方案模式下不显示导出按钮 -->
        <el-button v-if="dialogMode !== 'history'" type="primary" @click="exportPath">导出路径</el-button>
      </template>
    </el-dialog>

    <!-- 历史方案对话框 -->
    <el-dialog
      v-model="showHistoryDialog"
      title="历史实现路径方案"
      width="80%"
      :close-on-click-modal="false"
      class="history-path-dialog"
    >
      <div v-if="historyLoading" class="history-loading">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else-if="historyError" class="history-error">
        <el-alert :title="historyError" type="error" />
      </div>
      <div v-else-if="historyPathList && historyPathList.length > 0" class="history-list">
        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in historyPathList"
            :key="item.id"
            :timestamp="formatDateTime(item.created_at)"
            placement="top"
            :type="item.status === 'success' ? 'success' : 'danger'"
          >
            <el-card>
              <div class="history-item-header">
                <div>
                  <h4>方案 #{{ historyPathList.length - index }}</h4>
                  <p v-if="item.topic_description" style="margin: 5px 0; color: #909399; font-size: 13px;">
                    话题：{{ item.topic_description }}
                  </p>
                </div>
                <el-tag :type="item.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ item.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </div>
              <div class="history-item-content">
                <p><strong>使用的论文：</strong>{{ item.paper_ids.join(', ') }}</p>
                <p v-if="item.timings && item.timings.total_ms">
                  <strong>总耗时：</strong>{{ (item.timings.total_ms / 1000).toFixed(2) }} 秒
                </p>
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="viewHistoryPath(item)"
                  style="margin-top: 10px"
                >
                  查看详情
                </el-button>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
      <div v-else class="history-empty">
        <el-empty description="该话题下暂无历史方案" />
      </div>
      <template #footer>
        <el-button @click="showHistoryDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 所有历史方案对话框 -->
    <el-dialog
      v-model="showAllHistoryDialog"
      title="所有历史实现路径方案"
      width="85%"
      :close-on-click-modal="false"
      class="all-history-path-dialog"
    >
      <div v-if="allHistoryLoading" class="history-loading">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else-if="allHistoryError" class="history-error">
        <el-alert :title="allHistoryError" type="error" />
      </div>
      <div v-else-if="allHistoryPathList && allHistoryPathList.length > 0" class="all-history-list">
        <el-pagination
          v-model:current-page="allHistoryPage"
          v-model:page-size="allHistoryPageSize"
          :total="allHistoryTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadAllImplementationPathHistory"
          @current-change="loadAllImplementationPathHistory"
          style="margin-bottom: 20px"
        />
        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in allHistoryPathList"
            :key="item.id"
            :timestamp="formatDateTime(item.created_at)"
            placement="top"
            :type="item.status === 'success' ? 'success' : 'danger'"
          >
            <el-card>
              <div class="history-item-header">
                <div>
                  <h4>方案 #{{ allHistoryTotal - (allHistoryPage - 1) * allHistoryPageSize - index }}</h4>
                  <p v-if="item.topic_description" style="margin: 5px 0; color: #909399; font-size: 13px;">
                    话题：{{ item.topic_description }}
                  </p>
                </div>
                <el-tag :type="item.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ item.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </div>
              <div class="history-item-content">
                <p><strong>使用的论文：</strong>{{ item.paper_ids.join(', ') }}</p>
                <p v-if="item.timings && item.timings.total_ms">
                  <strong>总耗时：</strong>{{ (item.timings.total_ms / 1000).toFixed(2) }} 秒
                </p>
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="viewHistoryPath(item)"
                  style="margin-top: 10px"
                >
                  查看详情
                </el-button>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
        <el-pagination
          v-model:current-page="allHistoryPage"
          v-model:page-size="allHistoryPageSize"
          :total="allHistoryTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadAllImplementationPathHistory"
          @current-change="loadAllImplementationPathHistory"
          style="margin-top: 20px"
        />
      </div>
      <div v-else class="history-empty">
        <el-empty description="暂无历史方案" />
      </div>
      <template #footer>
        <el-button @click="showAllHistoryDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import { Search, FolderOpened, OfficeBuilding, User, Document, Opportunity, Calendar, Clock, Close, View } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const searchText = ref('')
const matchMode = ref('enterprise')
const loading = ref(false)
const showResults = ref(false)
const currentMatchMode = ref(null) // 记录当前匹配时的模式
const currentHistoryId = ref(null) // 当前匹配的历史ID

// 论文选择和实现路径相关
const selectedPaperIds = ref([])
const selectedPapers = computed(() => {
  // 只返回论文（成果不能生成实现路径）
  return matchResults.value.filter(item => 
    item.type === '论文' && item.paper_id && selectedPaperIds.value.includes(item.paper_id)
  )
})
// 当前任务状态管理（独立管理）
const currentTask = ref({
  taskId: null,
  status: 'idle', // 'idle' | 'generating' | 'completed' | 'error' | 'cancelled'
  selectedPaperIds: [], // 记录本次任务选择的论文ID列表
  progress: null,
  result: null,
  error: null,
  createdAt: null
})

// 对话框模式：控制显示内容
const dialogMode = ref('idle') // 'idle' | 'generating' | 'result' | 'history'
const showPathDialog = ref(false)

// 历史方案显示数据（独立于当前任务）
const viewingHistoryItem = ref(null)

// 轮询定时器
let pathProgressTimer = null
const cancellingPath = ref(false)

// 兼容旧代码的 computed 属性（逐步迁移）
const pathTaskId = computed(() => currentTask.value.taskId)
const pathLoading = computed(() => currentTask.value.status === 'generating')
const pathError = computed(() => currentTask.value.error)
const implementationPath = computed(() => currentTask.value.result?.implementation_path || null)
const papersAnalysis = computed(() => currentTask.value.result?.papers_analysis || currentTask.value.progress?.papers_analysis || [])
const pathTimings = computed(() => currentTask.value.result?.timings || null)
const pathProgress = computed(() => currentTask.value.progress)
const generatingPath = computed(() => currentTask.value.status === 'generating')

// 历史方案相关（当前话题）
const showHistoryDialog = ref(false)
const historyLoading = ref(false)
const historyError = ref(null)
const historyPathList = ref([])

// 所有历史方案相关
const showAllHistoryDialog = ref(false)
const allHistoryLoading = ref(false)
const allHistoryError = ref(null)
const allHistoryPathList = ref([])
const allHistoryPage = ref(1)
const allHistoryPageSize = ref(20)
const allHistoryTotal = ref(0)

// 保存匹配状态到 localStorage（只在查看合作方案后保存）
const saveMatchState = () => {
  const state = {
    searchText: searchText.value,
    matchMode: matchMode.value,
    hasResults: showResults.value,
    timestamp: Date.now(),
    userId: userStore.userInfo?.id || null // 保存当前用户ID
  }
  localStorage.setItem('smartMatchState', JSON.stringify(state))
}

// 恢复匹配状态（从合作方案详情返回时）
const restoreMatchState = () => {
  try {
    const currentUserId = userStore.userInfo?.id
    
    // 首先检查 URL 参数
    if (route.query.restore === 'true') {
      const saved = localStorage.getItem('smartMatchState')
      if (saved) {
        const state = JSON.parse(saved)
        
        // 检查用户ID是否匹配（如果状态中有用户ID）
        if (state.userId !== undefined && state.userId !== null) {
          if (currentUserId !== state.userId) {
            // 用户不匹配，清除状态
            localStorage.removeItem('smartMatchState')
            return false
          }
        }
        
        // 检查状态是否过期（30分钟内有效）
        const isExpired = Date.now() - state.timestamp > 30 * 60 * 1000
        
        if (!isExpired && state.hasResults) {
          // 恢复搜索内容和匹配模式
          searchText.value = state.searchText || route.query.searchText || ''
          matchMode.value = state.matchMode || route.query.matchMode || 'enterprise'
          
          // 恢复匹配结果
          if (state.results && state.results.length > 0) {
            matchResults.value = state.results
            showResults.value = true
            currentMatchMode.value = state.matchMode || 'enterprise'
          } else {
            showResults.value = false
          }
          
          // 滚动到结果区域
          setTimeout(() => {
            const resultsSection = document.querySelector('.results-section')
            if (resultsSection) {
              resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
          }, 100)
          return true
        } else {
          // 状态过期，清除
          localStorage.removeItem('smartMatchState')
        }
      }
    }
    
    // 如果没有 URL 参数，尝试从 localStorage 恢复
    const saved = localStorage.getItem('smartMatchState')
    if (saved) {
      const state = JSON.parse(saved)
      
      // 检查用户ID是否匹配（如果状态中有用户ID）
      if (state.userId !== undefined && state.userId !== null) {
        if (currentUserId !== state.userId) {
          // 用户不匹配，清除状态
          localStorage.removeItem('smartMatchState')
          return false
        }
      }
      
      const isExpired = Date.now() - state.timestamp > 30 * 60 * 1000
      
      if (!isExpired && state.hasResults && state.results) {
        searchText.value = state.searchText || ''
        matchMode.value = state.matchMode || 'enterprise'
        matchResults.value = state.results
        showResults.value = true
        currentMatchMode.value = state.matchMode || 'enterprise'
        return true
      } else if (isExpired) {
        // 状态过期，清除
        localStorage.removeItem('smartMatchState')
      }
    }
  } catch (e) {
    console.error('恢复匹配状态失败:', e)
    // 出错时清除状态
    localStorage.removeItem('smartMatchState')
  }
  return false
}

// 清除匹配状态
const clearMatchState = () => {
  localStorage.removeItem('smartMatchState')
}

// ==================== 实现路径任务管理 ====================

// 清理当前任务状态
const clearCurrentTask = () => {
  if (pathProgressTimer) {
    clearInterval(pathProgressTimer)
    pathProgressTimer = null
  }
  currentTask.value = {
    taskId: null,
    status: 'idle',
    selectedPaperIds: [],
    progress: null,
    result: null,
    error: null,
    createdAt: null
  }
  dialogMode.value = 'idle'
}

// 检查选择的论文是否与当前任务相同
const isSamePaperSelection = (paperIds) => {
  if (!currentTask.value.selectedPaperIds || currentTask.value.selectedPaperIds.length === 0) {
    return false
  }
  if (paperIds.length !== currentTask.value.selectedPaperIds.length) {
    return false
  }
  const sortedCurrent = [...currentTask.value.selectedPaperIds].sort()
  const sortedNew = [...paperIds].sort()
  return JSON.stringify(sortedCurrent) === JSON.stringify(sortedNew)
}

// 开始新任务
const startNewTask = async () => {
  if (selectedPaperIds.value.length === 0) {
    ElMessage.warning('请至少选择一篇论文')
    return
  }
  
  if (selectedPaperIds.value.length > 5) {
    ElMessage.warning('最多只能选择5篇论文')
    return
  }
  
  // 检查是否有正在生成的任务
  if (currentTask.value.status === 'generating') {
    ElMessage.warning('已有任务正在生成，请先取消或等待完成')
    return
  }
  
  // 检查是否选择了相同的论文
  if (isSamePaperSelection(selectedPaperIds.value)) {
    if (currentTask.value.status === 'completed') {
      ElMessage.info('已为这些论文生成过实现路径，请点击"查看生成结果"查看')
      return
    }
    if (currentTask.value.status === 'error') {
      ElMessage.info('这些论文的生成任务已失败，请点击"查看任务状态"查看详情')
      return
    }
  }
  
  // 清理旧任务状态（如果选择了不同的论文）
  if (currentTask.value.taskId && !isSamePaperSelection(selectedPaperIds.value)) {
    clearCurrentTask()
  }
  
  // 初始化新任务
  currentTask.value = {
    taskId: Date.now().toString(),
    status: 'generating',
    selectedPaperIds: [...selectedPaperIds.value],
    progress: null,
    result: null,
    error: null,
    createdAt: Date.now()
  }
  
  dialogMode.value = 'generating'
  showPathDialog.value = true
  
  // 启动任务
  try {
    const requestData = {
      paper_ids: selectedPaperIds.value,
      max_pages_per_paper: 20,
      task_id: currentTask.value.taskId
    }
    
    // 如果有历史ID，使用历史ID获取需求；否则使用当前搜索文本
    if (currentHistoryId.value) {
      requestData.history_id = currentHistoryId.value
    } else {
      requestData.user_requirement = searchText.value
    }
    
    // 启动进度轮询
    const pollProgress = async () => {
      if (!currentTask.value.taskId) return
      try {
        const res = await api.get(`/papers/implementation-progress/${currentTask.value.taskId}`)
        currentTask.value.progress = res.data
        
        // 检查任务是否被取消
        if (res.data.status === 'cancelled') {
          currentTask.value.status = 'cancelled'
          currentTask.value.error = '任务已取消'
          if (pathProgressTimer) {
            clearInterval(pathProgressTimer)
            pathProgressTimer = null
          }
          ElMessage.warning('任务已取消')
          return
        }
        
        // 检查任务是否完成
        if (res.data && res.data.result && (res.data.status === 'finished' || res.data.status === 'error')) {
          const result = res.data.result
          if (result.status === 'error') {
            currentTask.value.status = 'error'
            currentTask.value.error = result.error_message || '生成实现路径失败'
            ElMessage.error(currentTask.value.error)
          } else {
            currentTask.value.status = 'completed'
            currentTask.value.result = {
              implementation_path: result.implementation_path,
              papers_analysis: result.papers_analysis || res.data.papers_analysis || [],
              timings: result.timings || null
            }
            dialogMode.value = 'result'
            // 如果对话框未打开，自动打开显示结果
            if (!showPathDialog.value) {
              showPathDialog.value = true
            }
            ElMessage.success('实现路径生成成功！')
          }
          if (pathProgressTimer) {
            clearInterval(pathProgressTimer)
            pathProgressTimer = null
          }
          return
        }
        
        // 如果进度中包含 papers_analysis，更新显示
        if (res.data.papers_analysis && res.data.papers_analysis.length > 0) {
          // papers_analysis 已经在 progress 中，computed 会自动更新
        }
      } catch (e) {
        console.error('获取实现路径进度失败:', e)
      }
    }
    
    await pollProgress()
    pathProgressTimer = setInterval(pollProgress, 1000)
    
    // 发送生成请求
    const response = await api.post('/papers/generate-implementation-path', requestData)
    
    if (response.data.status === 'error') {
      currentTask.value.status = 'error'
      currentTask.value.error = response.data.error_message || '生成实现路径失败'
      ElMessage.error(currentTask.value.error)
      if (pathProgressTimer) {
        clearInterval(pathProgressTimer)
        pathProgressTimer = null
      }
    }
    
    // 等待结果（轮询已经在运行）
    const waitForResult = async () => {
      const maxWaitMs = 30 * 60 * 1000 // 最长等待 30 分钟
      const intervalMs = 1000
      let waited = 0
      
      while (waited <= maxWaitMs) {
        const progress = currentTask.value.progress
        
        // 检查任务是否被取消
        if (progress && progress.status === 'cancelled') {
          currentTask.value.status = 'cancelled'
          currentTask.value.error = '任务已取消'
          if (pathProgressTimer) {
            clearInterval(pathProgressTimer)
            pathProgressTimer = null
          }
          ElMessage.warning('任务已取消')
          return
        }
        
        // 检查任务是否完成
        if (progress && progress.result && (progress.status === 'finished' || progress.status === 'error')) {
          const result = progress.result
          if (result.status === 'error') {
            currentTask.value.status = 'error'
            currentTask.value.error = result.error_message || '生成实现路径失败'
            ElMessage.error(currentTask.value.error)
          } else {
            currentTask.value.status = 'completed'
            currentTask.value.result = {
              implementation_path: result.implementation_path,
              papers_analysis: result.papers_analysis || progress.papers_analysis || [],
              timings: result.timings || null
            }
            dialogMode.value = 'result'
            ElMessage.success('实现路径生成成功！')
          }
          return
        }
        
        await new Promise((resolve) => setTimeout(resolve, intervalMs))
        waited += intervalMs
      }
      
      // 超时兜底
      if (!currentTask.value.result) {
        currentTask.value.error = '生成实现路径超时，请稍后在对话框中重新点击生成或刷新页面后重试'
        ElMessage.error(currentTask.value.error)
      }
    }
    
    await waitForResult()
  } catch (error) {
    currentTask.value.status = 'error'
    currentTask.value.error = error.response?.data?.detail || error.message || '生成实现路径失败'
    ElMessage.error(currentTask.value.error)
    console.error('生成实现路径失败:', error)
    if (pathProgressTimer) {
      clearInterval(pathProgressTimer)
      pathProgressTimer = null
    }
  }
}

// 查看当前任务
const viewCurrentTask = () => {
  if (currentTask.value.status === 'idle') {
    ElMessage.warning('暂无任务')
    return
  }
  
  // 根据任务状态设置对话框模式
  if (currentTask.value.status === 'generating') {
    dialogMode.value = 'generating'
    // 恢复轮询
    if (!pathProgressTimer && currentTask.value.taskId) {
      const pollProgress = async () => {
        if (!currentTask.value.taskId) return
        try {
          const res = await api.get(`/papers/implementation-progress/${currentTask.value.taskId}`)
          currentTask.value.progress = res.data
          
          // 检查任务是否被取消
          if (res.data.status === 'cancelled') {
            currentTask.value.status = 'cancelled'
            currentTask.value.error = '任务已取消'
            if (pathProgressTimer) {
              clearInterval(pathProgressTimer)
              pathProgressTimer = null
            }
            ElMessage.warning('任务已取消')
            return
          }
          
          // 检查任务是否完成
          if (res.data && res.data.result && (res.data.status === 'finished' || res.data.status === 'error')) {
            const result = res.data.result
            if (result.status === 'error') {
              currentTask.value.status = 'error'
              currentTask.value.error = result.error_message || '生成实现路径失败'
              ElMessage.error(currentTask.value.error)
            } else {
              currentTask.value.status = 'completed'
              currentTask.value.result = {
                implementation_path: result.implementation_path,
                papers_analysis: result.papers_analysis || res.data.papers_analysis || [],
                timings: result.timings || null
              }
              dialogMode.value = 'result'
              // 如果对话框未打开，自动打开显示结果
              if (!showPathDialog.value) {
                showPathDialog.value = true
              }
              ElMessage.success('实现路径生成成功！')
            }
            if (pathProgressTimer) {
              clearInterval(pathProgressTimer)
              pathProgressTimer = null
            }
            return
          }
          
          // 如果进度中包含 papers_analysis，更新显示
          if (res.data.papers_analysis && res.data.papers_analysis.length > 0) {
            // papers_analysis 已经在 progress 中
          }
        } catch (e) {
          console.error('获取实现路径进度失败:', e)
        }
      }
      pollProgress()
      pathProgressTimer = setInterval(pollProgress, 1000)
    }
  } else if (currentTask.value.status === 'completed' || currentTask.value.status === 'error') {
    dialogMode.value = 'result'
  }
  
  // 只有在用户主动点击查看时才打开对话框
  // 如果对话框已经关闭（比如刚关闭了历史方案），不要自动打开
  showPathDialog.value = true
}

// 将后端返回的匹配结果转换为前端格式
const convertBackendMatchResults = (papers) => {
  return papers.map((paper, index) => {
    const score = paper.score || 0
    const matchScore = score > 1 ? Math.round(score) : Math.round(score * 100)
    
    // 根据item_type判断是论文还是成果
    const itemType = paper.item_type || (paper.paper_id && paper.paper_id.startsWith('achievement_') ? 'achievement' : 'paper')
    
    if (itemType === 'achievement') {
      // 成果格式
      return {
        id: `achievement_${paper.achievement_id || paper.paper_id?.replace('achievement_', '')}`,
        achievement_id: paper.achievement_id || parseInt(paper.paper_id?.replace('achievement_', '') || '0'),
        title: paper.name || paper.title || '无标题',
        summary: paper.description || paper.abstract || '暂无描述',
        application: paper.application || '',
        matchScore: matchScore,
        type: '成果',
        field: paper.field || paper.categories || '未分类',
        keywords: [],
        paper_id: null,
        pdf_url: null,
        authors: '',
        published_date: '',
        reason: paper.reason || '',
        match_type: paper.match_type || '',
        vector_score: paper.vector_score || 0,
        contact_name: paper.contact_name || '',
        contact_phone: paper.contact_phone || '',
        contact_email: paper.contact_email || '',
        cooperation_mode: paper.cooperation_mode || []
      }
    } else {
      // 论文格式
      return {
        id: paper.paper_id || `paper_${index}`,
        title: paper.title || '无标题',
        summary: paper.abstract || '暂无摘要',
        matchScore: matchScore,
        type: '论文',
        field: paper.categories || '未分类',
        keywords: paper.categories ? paper.categories.split(',') : [],
        paper_id: paper.paper_id,
        pdf_url: paper.pdf_url,
        authors: paper.authors || '',
        published_date: paper.published_date || '',
        reason: paper.reason || '',
        match_type: paper.match_type || '',
        vector_score: paper.vector_score || 0
      }
    }
  })
}

// 从后端数据库恢复匹配结果
const restoreFromBackendHistory = async (historyId) => {
  try {
    const response = await api.get(`/matching/history/${historyId}/results`)
    
    if (response.data && response.data.papers && response.data.papers.length > 0) {
      const convertedResults = convertBackendMatchResults(response.data.papers)
      
      // 恢复搜索内容和模式
      searchText.value = route.query.q || response.data.search_desc || ''
      matchMode.value = route.query.type || response.data.match_mode || 'enterprise'
      
      // 恢复匹配结果
      matchResults.value = convertedResults
      showResults.value = true
      currentMatchMode.value = matchMode.value
      cleanSelectedPaperIds()
      
      // 恢复历史ID
      if (response.data.history_id) {
        currentHistoryId.value = response.data.history_id
      } else if (historyId) {
        currentHistoryId.value = parseInt(historyId)
      }
      
      // 滚动到结果区域
      setTimeout(() => {
        const resultsSection = document.querySelector('.results-section')
        if (resultsSection) {
          resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 100)
      return true
    }
    return false
  } catch (e) {
    console.error('从后端恢复匹配结果失败:', e)
    return false
  }
}

// 从匹配历史恢复结果（从 localStorage）
const restoreFromHistory = (historyId) => {
  try {
    const currentUserId = userStore.userInfo?.id
    if (!currentUserId) {
      // 如果没有用户ID，无法恢复历史
      return false
    }
    
    // 使用用户ID作为key的一部分，确保只恢复当前用户的历史记录
    const historyKey = `matchHistory_${currentUserId}`
    const history = JSON.parse(localStorage.getItem(historyKey) || '[]')
    const historyItem = history.find(item => item.id === parseInt(historyId))
    
    if (historyItem && historyItem.results) {
      // 检查用户ID是否匹配（如果历史记录中有用户ID）
      if (historyItem.userId !== undefined && historyItem.userId !== null) {
        if (currentUserId !== historyItem.userId) {
          // 用户不匹配，不恢复
          return false
        }
      }
      
      // 恢复搜索内容和模式
      searchText.value = historyItem.searchContent
      matchMode.value = historyItem.matchMode
      currentMatchMode.value = historyItem.matchMode
      
      // 恢复匹配结果
      if (historyItem.results && historyItem.results.length > 0) {
        matchResults.value = historyItem.results
        showResults.value = true
        // 清理 selectedPaperIds，确保不会有无效值
        cleanSelectedPaperIds()
      } else {
        showResults.value = false
      }
      
      // 滚动到结果区域
      setTimeout(() => {
        const resultsSection = document.querySelector('.results-section')
        if (resultsSection) {
          resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 100)
      
      return true
    }
  } catch (e) {
    console.error('恢复匹配历史失败:', e)
  }
  return false
}

// 轮询检查匹配任务是否完成
let matchTaskPollTimer = null

const checkMatchTaskStatus = async () => {
  try {
    const taskStateStr = localStorage.getItem('smartMatchTaskState')
    if (!taskStateStr) {
      return false
    }
    
    const taskState = JSON.parse(taskStateStr)
    
    // 检查用户ID是否匹配（如果任务状态中有用户ID）
    // 如果当前用户ID与任务状态中的用户ID不匹配，说明是不同用户的任务，应该清除
    if (taskState.userId !== undefined && taskState.userId !== null) {
      const currentUserId = userStore.userInfo?.id
      if (currentUserId !== taskState.userId) {
        // 用户不匹配，清除任务状态
        localStorage.removeItem('smartMatchTaskState')
        return false
      }
    }
    
    // 检查任务是否过期（超过10分钟）
    if (Date.now() - taskState.timestamp > 10 * 60 * 1000) {
      localStorage.removeItem('smartMatchTaskState')
      return false
    }
    
    // 如果任务已完成，直接恢复结果
    if (taskState.status === 'completed' && taskState.results) {
      searchText.value = taskState.searchText
      matchMode.value = taskState.matchMode
      matchResults.value = taskState.results
      showResults.value = true
      currentMatchMode.value = taskState.matchMode
      if (taskState.historyId) {
        currentHistoryId.value = taskState.historyId
      }
      loading.value = false
      // 清理 selectedPaperIds，确保不会有无效值
      cleanSelectedPaperIds()
      localStorage.removeItem('smartMatchTaskState')
      if (matchTaskPollTimer) {
        clearInterval(matchTaskPollTimer)
        matchTaskPollTimer = null
      }
      ElMessage.success(`匹配完成！找到 ${taskState.results.length} 个匹配项`)
      // 滚动到结果区域
      setTimeout(() => {
        const resultsSection = document.querySelector('.results-section')
        if (resultsSection) {
          resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 100)
      return true
    }
    
    // 如果任务失败，显示错误
    if (taskState.status === 'failed') {
      searchText.value = taskState.searchText
      matchMode.value = taskState.matchMode
      loading.value = false
      localStorage.removeItem('smartMatchTaskState')
      if (matchTaskPollTimer) {
        clearInterval(matchTaskPollTimer)
        matchTaskPollTimer = null
      }
      ElMessage.error('匹配失败: ' + (taskState.error || '未知错误'))
      return true
    }
    
    // 如果任务正在进行中，继续轮询（等待startMatch函数更新状态）
    if (taskState.status === 'matching') {
      return false
    }
    
    return false
  } catch (e) {
    console.error('检查匹配任务状态失败:', e)
    return false
  }
}

// 根据用户角色自动设置默认模式，并处理路由参数
onMounted(async () => {
  // 清理 selectedPaperIds 中的无效值（null、undefined 等）
  cleanSelectedPaperIds()
  
  // 检查是否有正在进行的匹配任务
  const taskStateStr = localStorage.getItem('smartMatchTaskState')
  if (taskStateStr) {
    try {
      const taskState = JSON.parse(taskStateStr)
      
      // 检查用户ID是否匹配（如果任务状态中有用户ID）
      // 如果当前用户ID与任务状态中的用户ID不匹配，说明是不同用户的任务，应该清除
      if (taskState.userId !== undefined && taskState.userId !== null) {
        const currentUserId = userStore.userInfo?.id
        if (currentUserId !== taskState.userId) {
          // 用户不匹配，清除任务状态
          localStorage.removeItem('smartMatchTaskState')
        } else {
          // 用户匹配，继续检查任务是否过期
          if (Date.now() - taskState.timestamp > 10 * 60 * 1000) {
            localStorage.removeItem('smartMatchTaskState')
          } else {
            // 如果任务已完成或失败，直接恢复
            const hasActiveTask = await checkMatchTaskStatus()
            if (hasActiveTask) {
              return
            }
            
            // 如果任务正在进行中，恢复状态并启动轮询
            if (taskState.status === 'matching') {
              searchText.value = taskState.searchText
              matchMode.value = taskState.matchMode
              loading.value = true
              showResults.value = false
              
              // 启动轮询，每2秒检查一次
              matchTaskPollTimer = setInterval(async () => {
                const restored = await checkMatchTaskStatus()
                if (restored && matchTaskPollTimer) {
                  clearInterval(matchTaskPollTimer)
                  matchTaskPollTimer = null
                }
              }, 2000)
              
              // 立即检查一次
              await checkMatchTaskStatus()
              return
            }
          }
        }
      } else {
        // 旧版本的任务状态（没有用户ID），检查是否过期
        if (Date.now() - taskState.timestamp > 10 * 60 * 1000) {
          localStorage.removeItem('smartMatchTaskState')
        } else {
          // 如果任务已完成或失败，直接恢复
          const hasActiveTask = await checkMatchTaskStatus()
          if (hasActiveTask) {
            return
          }
          
          // 如果任务正在进行中，恢复状态并启动轮询
          if (taskState.status === 'matching') {
            searchText.value = taskState.searchText
            matchMode.value = taskState.matchMode
            loading.value = true
            showResults.value = false
            
            // 启动轮询，每2秒检查一次
            matchTaskPollTimer = setInterval(async () => {
              const restored = await checkMatchTaskStatus()
              if (restored && matchTaskPollTimer) {
                clearInterval(matchTaskPollTimer)
                matchTaskPollTimer = null
              }
            }, 2000)
            
            // 立即检查一次
            await checkMatchTaskStatus()
            return
          }
        }
      }
    } catch (e) {
      console.error('恢复匹配任务状态失败:', e)
      localStorage.removeItem('smartMatchTaskState')
    }
  }
  
  // 优先检查是否从匹配历史跳转过来（应该优先恢复历史记录，而不是当前页面的状态）
  if (route.query.fromHistory === 'true' || route.query.historyId) {
    // 如果从匹配历史跳转过来，从 sessionStorage 加载结果
    if (route.query.fromHistory === 'true') {
      try {
        const currentUserId = userStore.userInfo?.id
        const sessionResults = sessionStorage.getItem('matchingResults')
        if (sessionResults) {
          const data = JSON.parse(sessionResults)
          
          // 检查用户ID是否匹配（如果sessionStorage中有用户ID）
          if (data.userId !== undefined && data.userId !== null) {
            if (currentUserId !== data.userId) {
              // 用户不匹配，清除sessionStorage并返回
              sessionStorage.removeItem('matchingResults')
              showResults.value = false
              ElMessage.warning('匹配结果不属于当前用户，请重新匹配')
              return
            }
          }
          
          const papers = data.papers || []
          
          if (papers.length > 0) {
            // 恢复搜索内容和模式
            searchText.value = route.query.q || data.searchText || ''
            matchMode.value = route.query.type || data.matchMode || 'enterprise'
            
            // 恢复匹配结果
            matchResults.value = papers
            showResults.value = true
            currentMatchMode.value = matchMode.value
            // 清理 selectedPaperIds，确保不会有无效值
            cleanSelectedPaperIds()
            
            // 如果有历史ID，也需要恢复
            if (data.historyId) {
              currentHistoryId.value = data.historyId
            }
            
            // 清除 sessionStorage（避免重复使用）
            sessionStorage.removeItem('matchingResults')
            
            // 滚动到结果区域
            setTimeout(() => {
              const resultsSection = document.querySelector('.results-section')
              if (resultsSection) {
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }
            }, 100)
            return // 已处理，直接返回
          } else {
            showResults.value = false
            ElMessage.warning('匹配结果数据为空，请重新匹配')
            return
          }
        } else {
          // sessionStorage 中没有数据，可能是刷新页面，尝试从后端数据库恢复
          if (route.query.historyId) {
            const restored = await restoreFromBackendHistory(route.query.historyId)
            if (restored) {
              return // 已恢复，直接返回
            }
            // 如果后端恢复失败，尝试从 localStorage 恢复
            const restoredFromLocal = restoreFromHistory(route.query.historyId)
            if (restoredFromLocal) {
              return // 已恢复，直接返回
            }
          }
          // 如果既没有 sessionStorage 也没有 historyId，静默处理（不弹出警告，可能是刷新页面）
          showResults.value = false
          // 不弹出警告，因为可能是刷新页面导致的
          return
        }
      } catch (e) {
        console.error('从匹配历史恢复失败:', e)
        showResults.value = false
        // 尝试从后端数据库恢复
        if (route.query.historyId) {
          const restored = await restoreFromBackendHistory(route.query.historyId)
          if (restored) {
            return
          }
          // 如果后端恢复失败，尝试从 localStorage 恢复
          const restoredFromLocal = restoreFromHistory(route.query.historyId)
          if (restoredFromLocal) {
            return
          }
        }
        // 静默处理错误，不弹出警告（可能是刷新页面导致的）
      }
      return // 已处理历史记录恢复，直接返回
    }
    
    // 如果从匹配历史跳转过来，恢复历史记录（通过 historyId）
    if (route.query.historyId) {
      // 优先从后端数据库恢复（刷新后 sessionStorage 已清除）
      const restored = await restoreFromBackendHistory(route.query.historyId)
      if (restored) {
        return // 已恢复，直接返回
      }
      // 如果后端恢复失败，尝试从 localStorage 恢复
      const restoredFromLocal = restoreFromHistory(route.query.historyId)
      if (restoredFromLocal) {
        return // 已恢复，直接返回
      }
    }
  }
  
  // 检查是否从合作方案详情返回（有保存的状态）
  const restored = restoreMatchState()
  
  if (!restored) {
    // 如果没有保存的状态，处理从匹配历史页面传递的参数（旧版本兼容）
    if (route.query.q) {
      searchText.value = route.query.q.toString()
    }
    if (route.query.type) {
      const type = route.query.type.toString()
      if (type === 'enterprise' || type === 'researcher') {
        matchMode.value = type
      }
    } else if (userStore.userInfo?.role) {
      // 如果没有传递类型参数，则使用用户角色
      matchMode.value = userStore.userInfo.role
    } else {
      // 新进入页面时，清除之前的状态（但保留匹配结果数据，以便从合作方案返回时使用）
      showResults.value = false
      currentMatchMode.value = null
      // 不清除 matchResults，因为可能从合作方案页面返回
    }
  }
})

// 组件卸载时清理轮询定时器
onUnmounted(() => {
  if (matchTaskPollTimer) {
    clearInterval(matchTaskPollTimer)
    matchTaskPollTimer = null
  }
  
  // 清理实现路径生成的轮询和取消任务
  if (pathProgressTimer) {
    clearInterval(pathProgressTimer)
    pathProgressTimer = null
  }
  
  // 如果正在生成实现路径，尝试取消
  if (pathLoading.value && pathTaskId.value) {
    // 异步取消，不等待结果
    api.post(`/papers/cancel-implementation-path/${pathTaskId.value}`).catch(() => {
      // 忽略错误，因为组件已经卸载
    })
  }
})

// 存储从API获取的真实匹配结果
const matchResults = ref([])

// 根据匹配模式过滤结果（现在使用真实数据）
const filteredResults = computed(() => {
  // 如果没有结果显示，返回空数组
  if (!showResults.value) {
    return []
  }
  
  // 如果切换了模式，不显示结果（需要重新匹配）
  if (currentMatchMode.value && matchMode.value !== currentMatchMode.value) {
    return []
  }
  
  // 直接返回从API获取的真实匹配结果
  // 后端返回的是论文数据，统一作为成果显示
  return matchResults.value
})

// 监听匹配模式变化
watch(matchMode, (newMode, oldMode) => {
  // 如果已经有结果显示，且切换了模式，则隐藏结果
  if (showResults.value && currentMatchMode.value && newMode !== currentMatchMode.value) {
    showResults.value = false
    currentMatchMode.value = null
  }
})

// 保存匹配历史到 localStorage
const saveMatchHistory = () => {
  try {
    const currentUserId = userStore.userInfo?.id
    if (!currentUserId) {
      // 如果没有用户ID，不保存历史
      return
    }
    
    // 使用用户ID作为key的一部分，确保每个用户有独立的历史记录
    const historyKey = `matchHistory_${currentUserId}`
    let history = JSON.parse(localStorage.getItem(historyKey) || '[]')
    
    // 获取当前匹配的结果（使用真实数据）
    const currentResults = matchResults.value
    
    const historyItem = {
      id: Date.now(), // 使用时间戳作为ID
      matchTime: new Date().toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }),
      searchContent: searchText.value,
      matchType: matchMode.value === 'enterprise' ? '找成果' : '找需求',
      matchCount: currentResults.length,
      results: currentResults, // 保存完整的匹配结果
      matchMode: matchMode.value,
      userId: currentUserId // 保存用户ID
    }
    
    // 添加到历史记录开头（最新的在前面）
    history.unshift(historyItem)
    
    // 只保留最近50条记录
    if (history.length > 50) {
      history = history.slice(0, 50)
    }
    
    localStorage.setItem(historyKey, JSON.stringify(history))
  } catch (e) {
    console.error('保存匹配历史失败:', e)
  }
}

// 开始匹配
const startMatch = async () => {
  if (!searchText.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  
  // 检查输入是否有意义（至少包含一些有意义的字符，避免全是重复字符）
  const trimmedText = searchText.value.trim()
  if (trimmedText.length < 5) {
    ElMessage.warning('请输入至少5个字符的搜索内容')
    return
  }
  
  // 检查是否全是重复字符（简单检测：如果前10个字符都相同，且整个文本长度超过50，可能是无意义输入）
  if (trimmedText.length > 50) {
    const firstChar = trimmedText[0]
    const firstTenChars = trimmedText.substring(0, Math.min(10, trimmedText.length))
    if (firstTenChars.split('').every(char => char === firstChar)) {
      // 检查是否整个文本都是同一个字符
      const uniqueChars = new Set(trimmedText.split(''))
      if (uniqueChars.size <= 2) { // 允许最多2个不同字符（比如"aa"或"ab"）
        ElMessage.warning('请输入有意义的搜索内容，避免使用重复字符')
        return
      }
    }
  }

  loading.value = true
  showResults.value = false

  // 清除之前保存的状态（新匹配时）
  clearMatchState()

  // 保存正在进行的匹配任务状态（用于页面切换后恢复）
  // 保存用户ID，确保只有同一用户才能恢复任务状态
  const matchTaskState = {
    searchText: searchText.value,
    matchMode: matchMode.value,
    loading: true,
    timestamp: Date.now(),
    status: 'matching', // matching, completed, failed
    userId: userStore.userInfo?.id || null // 保存当前用户ID
  }
  localStorage.setItem('smartMatchTaskState', JSON.stringify(matchTaskState))

  try {
    // 调用统一匹配API（包含论文和成果）
    const response = await api.post('/matching/match-all', {
      requirement: searchText.value,
      top_k: 50,
      match_mode: matchMode.value,
      save_history: true  // 自动保存匹配历史
    })

    // 后端返回的混合结果（论文和成果）
    const items = response.data.papers || []
    const convertedResults = items.map((item, index) => {
      // 后端返回的 score 是 0-100 的整数
      const score = item.score || item.similarity_score || 0
      const matchScore = score > 1 ? Math.round(score) : Math.round(score * 100)
      
      // 根据 item_type 区分论文和成果
      if (item.item_type === 'achievement') {
        // 成果格式
        return {
          id: `achievement_${item.achievement_id}`,
          achievement_id: item.achievement_id,
          title: item.name || '无标题',
          summary: item.description || '暂无描述',
          application: item.application || '',
          matchScore: matchScore,
          type: '成果',
          field: item.field || '未分类',
          keywords: [],
          paper_id: null, // 成果没有 paper_id
          pdf_url: null, // 成果没有 PDF
          authors: '', // 成果没有作者
          published_date: '',
          reason: item.reason || '',
          match_type: item.match_type || '',
          vector_score: item.vector_score || 0,
          // 成果特有字段
          contact_name: item.contact_name || '',
          contact_phone: item.contact_phone || '',
          contact_email: item.contact_email || '',
          cooperation_mode: item.cooperation_mode || []
        }
      } else {
        // 论文格式
        return {
          id: item.paper_id || `paper_${index}`,
          title: item.title || '无标题',
          summary: item.abstract || item.desc || '暂无摘要',
          matchScore: matchScore,
          type: '论文',
          field: item.categories || '未分类',
          keywords: item.categories ? item.categories.split(',') : [],
          paper_id: item.paper_id,
          pdf_url: item.pdf_url,
          authors: item.authors || '',
          published_date: item.published_date || '',
          reason: item.reason || '',
          match_type: item.match_type || '',
          vector_score: item.vector_score || 0
        }
      }
    })

    // 更新结果数据（使用真实数据）
    matchResults.value = convertedResults

    // 停止轮询（如果正在运行）
    if (matchTaskPollTimer) {
      clearInterval(matchTaskPollTimer)
      matchTaskPollTimer = null
    }
    
    loading.value = false
    
    // 检查是否有匹配结果
    if (convertedResults.length === 0) {
      showResults.value = false
      ElMessage.warning('未找到匹配结果，请尝试使用更具体、有意义的搜索内容')
      
      // 更新任务状态为失败，然后清除（让轮询能够检测到）
      const failedTaskState = {
        ...matchTaskState,
        status: 'failed',
        error: '未找到匹配结果'
      }
      localStorage.setItem('smartMatchTaskState', JSON.stringify(failedTaskState))
      // 延迟清除，确保轮询能够检测到
      setTimeout(() => {
        localStorage.removeItem('smartMatchTaskState')
      }, 1000)
      return
    }
    
    showResults.value = true
    // 记录当前匹配时的模式
    currentMatchMode.value = matchMode.value

    // 保存匹配历史到 localStorage（作为本地备份）
    saveMatchHistory()
    
    // 后端已经自动保存到数据库，这里显示成功消息
    const historyId = response.data.history_id
    if (historyId) {
      currentHistoryId.value = historyId  // 保存当前话题的历史ID
    } else {
      currentHistoryId.value = null
    }
    
    // 更新任务状态为已完成，保存结果（让轮询能够检测到并恢复）
    const completedTaskState = {
      ...matchTaskState,
      status: 'completed',
      results: convertedResults,
      historyId: historyId
    }
    localStorage.setItem('smartMatchTaskState', JSON.stringify(completedTaskState))
    
    // 显示成功消息
    if (historyId) {
      ElMessage.success(`匹配完成！找到 ${convertedResults.length} 个匹配项，已保存到匹配历史`)
    } else {
      ElMessage.success(`匹配完成！找到 ${convertedResults.length} 个匹配项`)
    }
    
    // 延迟清除任务状态（确保轮询能够检测到完成状态）
    setTimeout(() => {
      localStorage.removeItem('smartMatchTaskState')
    }, 2000)

    // 滚动到结果区域
    setTimeout(() => {
      const resultsSection = document.querySelector('.results-section')
      if (resultsSection) {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 100)
  } catch (error) {
    // 停止轮询（如果正在运行）
    if (matchTaskPollTimer) {
      clearInterval(matchTaskPollTimer)
      matchTaskPollTimer = null
    }
    
    loading.value = false
    showResults.value = false
    
    // 更新任务状态为失败，然后清除（让轮询能够检测到）
    const failedTaskState = {
      ...matchTaskState,
      status: 'failed',
      error: error.response?.data?.detail || error.message || '未知错误'
    }
    localStorage.setItem('smartMatchTaskState', JSON.stringify(failedTaskState))
    
    // 延迟清除，确保轮询能够检测到
    setTimeout(() => {
      localStorage.removeItem('smartMatchTaskState')
    }, 1000)
    
    ElMessage.error('匹配失败: ' + (error.response?.data?.detail || error.message))
    console.error('匹配失败:', error)
  }
}

// 获取匹配度颜色
const getScoreColor = (score) => {
  if (score >= 90) return '#67c23a' // 绿色
  if (score >= 80) return '#409eff' // 蓝色
  if (score >= 70) return '#e6a23c' // 橙色
  return '#f56c6c' // 红色
}

// 高亮关键词
const highlightKeywords = (text) => {
  if (!text) return ''
  
  // 从搜索结果中提取关键词（这里简化处理，实际应该从匹配结果中获取）
  const keywords = searchText.value.split(/\s+/).filter(k => k.length > 1)
  
  let highlighted = text
  keywords.forEach(keyword => {
    if (keyword.length > 1) {
      const regex = new RegExp(`(${keyword})`, 'gi')
      highlighted = highlighted.replace(regex, '<mark class="highlight">$1</mark>')
    }
  })
  
  return highlighted
}

// 论文选择相关函数
const isPaperSelected = (paperId) => {
  // 只处理有效的 paper_id（不能是 null 或 undefined）
  if (!paperId) return false
  return selectedPaperIds.value.includes(paperId)
}

const handlePaperSelection = (paperId, checked) => {
  // 只处理有效的 paper_id（不能是 null 或 undefined）
  if (!paperId) return
  
  if (checked && !selectedPaperIds.value.includes(paperId)) {
    selectedPaperIds.value.push(paperId)
  } else if (!checked) {
    selectedPaperIds.value = selectedPaperIds.value.filter(id => id !== paperId)
  }
  
  // 限制最多选择5篇
  if (selectedPaperIds.value.length > 5) {
    ElMessage.warning('最多只能选择5篇论文进行分析')
    selectedPaperIds.value = selectedPaperIds.value.slice(0, 5)
  }
}

// selectedPapers 已经只包含论文了（在 computed 中已过滤），所以直接检查长度即可

const clearSelection = () => {
  selectedPaperIds.value = []
  ElMessage.info('已清空选择')
}

// 清理 selectedPaperIds 中的无效值（null、undefined 等）
const cleanSelectedPaperIds = () => {
  selectedPaperIds.value = selectedPaperIds.value.filter(id => id != null && id !== undefined && id !== '')
}

// 旧的生成实现路径函数（已废弃，使用 startNewTask 代替）
// 保留此函数以避免破坏其他地方的引用，但实际调用 startNewTask
const generateImplementationPath = async () => {
  return startNewTask()
}

// 旧的生成实现路径函数（已废弃，保留用于兼容）
const _old_generateImplementationPath = async () => {
  if (selectedPaperIds.value.length === 0) {
    ElMessage.warning('请至少选择一篇论文')
    return
  }
  
  if (selectedPaperIds.value.length > 5) {
    ElMessage.warning('最多只能选择5篇论文')
    return
  }
  
  // 如果已经有任务在运行，直接打开对话框并恢复轮询
  if (pathTaskId.value && pathLoading.value) {
    showPathDialog.value = true
    // 恢复轮询
    if (!pathProgressTimer) {
      const pollProgress = async () => {
        if (!pathTaskId.value) return
        try {
          const res = await api.get(`/papers/implementation-progress/${pathTaskId.value}`)
          pathProgress.value = res.data
          
          // 检查任务是否被取消
          if (res.data.status === 'cancelled') {
            pathLoading.value = false
            generatingPath.value = false
            pathError.value = '任务已取消'
            if (pathProgressTimer) {
              clearInterval(pathProgressTimer)
              pathProgressTimer = null
            }
            ElMessage.warning('任务已取消')
            return
          }
          
          // 检查任务是否完成
          if (res.data && res.data.result && (res.data.status === 'finished' || res.data.status === 'error')) {
            const result = res.data.result
            if (result.status === 'error') {
              pathError.value = result.error_message || '生成实现路径失败'
              ElMessage.error(pathError.value)
            } else {
              implementationPath.value = result.implementation_path
              papersAnalysis.value = result.papers_analysis || res.data.papers_analysis || []
              pathTimings.value = result.timings || null
              pathLoading.value = false
              generatingPath.value = false
              ElMessage.success('实现路径生成成功！')
            }
            if (pathProgressTimer) {
              clearInterval(pathProgressTimer)
              pathProgressTimer = null
            }
            return
          }
          
          // 如果进度中包含 papers_analysis，更新前端显示
          if (res.data.papers_analysis && res.data.papers_analysis.length > 0) {
            papersAnalysis.value = res.data.papers_analysis
          }
        } catch (e) {
          console.error('获取实现路径进度失败:', e)
        }
      }
      await pollProgress()
      pathProgressTimer = setInterval(pollProgress, 1000)
    }
    return
  }
  
  // 新任务：重置状态
  generatingPath.value = true
  showPathDialog.value = true
  pathLoading.value = true
  pathError.value = null
  implementationPath.value = null
  papersAnalysis.value = []
  pathTimings.value = null
  pathProgress.value = null

  // 为本次任务生成一个ID，用于后端进度跟踪
  pathTaskId.value = Date.now().toString()
  
  try {
    const requestData = {
      paper_ids: selectedPaperIds.value,
      max_pages_per_paper: 20,
      task_id: pathTaskId.value
    }
    
    // 如果有历史ID，使用历史ID获取需求；否则使用当前搜索文本
    if (currentHistoryId.value) {
      requestData.history_id = currentHistoryId.value
    } else {
      requestData.user_requirement = searchText.value
    }
    
    // 启动进度轮询
    if (pathTaskId.value) {
      const pollProgress = async () => {
        if (!pathTaskId.value) return
        try {
          const res = await api.get(`/papers/implementation-progress/${pathTaskId.value}`)
          pathProgress.value = res.data
          
          // 检查任务是否被取消
          if (res.data.status === 'cancelled') {
            pathLoading.value = false
            generatingPath.value = false
            pathError.value = '任务已取消'
            if (pathProgressTimer) {
              clearInterval(pathProgressTimer)
              pathProgressTimer = null
            }
            ElMessage.warning('任务已取消')
            return
          }
          
          // 如果进度中包含 papers_analysis，更新前端显示（任务进行中也能看到已完成的论文分析）
          if (res.data.papers_analysis && res.data.papers_analysis.length > 0) {
            papersAnalysis.value = res.data.papers_analysis
          }
        } catch (e) {
          console.error('获取实现路径进度失败:', e)
        }
      }
      await pollProgress()
      pathProgressTimer = setInterval(pollProgress, 1000)
    }

    const response = await api.post('/papers/generate-implementation-path', requestData)

    // 后端现在可能返回：
    // - 本地模式: { status: 'processing', task_id, mode: 'local' }
    // - Redis 模式: { status: 'queued', task_id, mode: 'redis' }
    // 实际的实现路径结果会在进度接口返回的 state.result 中

    if (response.data.status === 'error') {
      pathError.value = response.data.error_message || '生成实现路径失败'
      ElMessage.error(pathError.value)
    } else {
      // 等待轮询任务把最终结果写入 pathProgress
      const waitForResult = async () => {
        const maxWaitMs = 30 * 60 * 1000 // 最长等待 30 分钟
        const intervalMs = 1000
        let waited = 0

        // 如果前面已经拿到一次 progress，这里可能已经有 result
        while (waited <= maxWaitMs) {
          const progress = pathProgress.value
          
          // 检查任务是否被取消
          if (progress && progress.status === 'cancelled') {
            pathLoading.value = false
            generatingPath.value = false
            pathError.value = '任务已取消'
            if (pathProgressTimer) {
              clearInterval(pathProgressTimer)
              pathProgressTimer = null
            }
            ElMessage.warning('任务已取消')
            return
          }
          
          // 如果进度中有 papers_analysis，先更新显示（任务进行中也能看到已完成的论文分析）
          if (progress && progress.papers_analysis && progress.papers_analysis.length > 0) {
            papersAnalysis.value = progress.papers_analysis
          }
          
          // 检查任务是否完成
          if (progress && progress.result && (progress.status === 'finished' || progress.status === 'error')) {
            const result = progress.result
            if (result.status === 'error') {
              pathError.value = result.error_message || '生成实现路径失败'
              ElMessage.error(pathError.value)
            } else {
              implementationPath.value = result.implementation_path
              // 优先使用 result 中的 papers_analysis（更完整），否则使用进度中的
              papersAnalysis.value = result.papers_analysis || progress.papers_analysis || []
              pathTimings.value = result.timings || null
              ElMessage.success('实现路径生成成功！')
            }
            return
          }
          await new Promise((resolve) => setTimeout(resolve, intervalMs))
          waited += intervalMs
        }

        // 超时兜底：如果还没有 result，就提示用户稍后重试
        if (!implementationPath.value) {
          pathError.value = '生成实现路径超时，请稍后在对话框中重新点击生成或刷新页面后重试'
          ElMessage.error(pathError.value)
        }
      }

      await waitForResult()
    }
  } catch (error) {
    pathError.value = error.response?.data?.detail || error.message || '生成实现路径失败'
    ElMessage.error(pathError.value)
    console.error('生成实现路径失败:', error)
    // 如果任务还在运行（有 pathTaskId），不要重置 generatingPath，以便用户可以重新打开对话框
    if (!pathTaskId.value) {
      generatingPath.value = false
    }
  } finally {
    // 只有在任务真正失败或完成时才重置 generatingPath
    // 如果任务还在运行（pathTaskId 存在），保持状态以便用户可以重新打开对话框
    if (!pathTaskId.value || !pathLoading.value) {
      generatingPath.value = false
    }
    // pathLoading 在任务完成或失败时会被设置为 false，但在任务运行时应该保持 true
  }
}

// 取消实现路径生成
const cancelImplementationPath = async () => {
  if (!currentTask.value.taskId) {
    // 如果没有任务ID，直接关闭对话框
    showPathDialog.value = false
    return
  }
  
  try {
    cancellingPath.value = true
    await api.post(`/papers/cancel-implementation-path/${currentTask.value.taskId}`)
    ElMessage.success('已取消生成实现路径')
    
    // 停止轮询
    if (pathProgressTimer) {
      clearInterval(pathProgressTimer)
      pathProgressTimer = null
    }
    
    // 更新状态
    currentTask.value.status = 'cancelled'
    currentTask.value.error = '任务已取消'
    if (currentTask.value.progress) {
      currentTask.value.progress.status = 'cancelled'
      currentTask.value.progress.current_step = '任务已取消'
    }
    
    // 关闭对话框
    showPathDialog.value = false
    dialogMode.value = 'idle'
  } catch (error) {
    ElMessage.error('取消任务失败: ' + (error.response?.data?.detail || error.message))
    console.error('取消实现路径失败:', error)
  } finally {
    cancellingPath.value = false
  }
}

// 处理对话框关闭
const handlePathDialogClose = () => {
  // 如果是在查看历史方案，关闭所有对话框，回到主界面
  if (dialogMode.value === 'history') {
    // 先关闭所有对话框
    showPathDialog.value = false
    showHistoryDialog.value = false
    // 延迟清理数据和重置 dialogMode，确保在关闭动画完成后再执行
    // Element Plus 对话框关闭动画大约 300ms，延迟 400ms 确保动画完成
    setTimeout(() => {
      // 再次确认对话框已关闭，避免状态不一致
      if (!showPathDialog.value && !showHistoryDialog.value) {
        viewingHistoryItem.value = null
        dialogMode.value = 'idle'
      }
    }, 400)
    return
  }
  
  // 只关闭对话框，不取消任务，不清理状态
  // 停止轮询（节省资源），但保留所有状态，以便重新打开时可以恢复
  if (pathProgressTimer) {
    clearInterval(pathProgressTimer)
    pathProgressTimer = null
  }
  // 不重置 currentTask 状态
  // 这样用户重新打开对话框时，可以继续查看进度或结果
  dialogMode.value = 'idle'
}

// 导出实现路径
const exportPath = () => {
  if (!implementationPath.value) {
    ElMessage.warning('没有可导出的内容')
    return
  }
  
  const content = JSON.stringify(implementationPath.value, null, 2)
  const blob = new Blob([content], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `实现路径_${new Date().getTime()}.json`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

// 查看合作方案
const viewProposal = (id) => {
  // 保存当前状态和匹配结果后再跳转
  const state = {
    searchText: searchText.value,
    matchMode: matchMode.value,
    hasResults: showResults.value,
    results: matchResults.value, // 保存完整的匹配结果
    timestamp: Date.now(),
    userId: userStore.userInfo?.id || null // 保存当前用户ID
  }
  localStorage.setItem('smartMatchState', JSON.stringify(state))
  
  router.push({
    path: `/proposal/${id}`,
    query: {
      from: 'smart-match'
    }
  })
}

// 打开PDF
const openPdf = (url) => {
  if (url) {
    window.open(url, '_blank')
  }
}

// 复制联系方式
const copyContact = (item) => {
  const contactInfo = `联系人：${item.contact_name || ''}\n电话：${item.contact_phone || ''}\n邮箱：${item.contact_email || ''}`
  navigator.clipboard.writeText(contactInfo).then(() => {
    ElMessage.success('联系方式已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch (e) {
    return dateStr
  }
}

// 获取匹配类型标签类型
const getMatchTypeTagType = (matchType) => {
  if (matchType && matchType.includes('S级')) return 'success'
  if (matchType && matchType.includes('A级')) return 'warning'
  if (matchType && matchType.includes('B级')) return 'info'
  return ''
}

// 加载实现路径历史
const loadImplementationPathHistory = async () => {
  if (!currentHistoryId.value) {
    historyError.value = '当前话题没有历史ID'
    return
  }
  
  historyLoading.value = true
  historyError.value = null
  historyPathList.value = []
  
  try {
    const response = await api.get(`/papers/implementation-path-history/${currentHistoryId.value}`)
    historyPathList.value = response.data.items || []
  } catch (error) {
    historyError.value = error.response?.data?.detail || error.message || '加载历史方案失败'
    ElMessage.error(historyError.value)
  } finally {
    historyLoading.value = false
  }
}

// 查看历史方案详情
const viewHistoryPath = (historyItem) => {
  if (historyItem.status !== 'success') {
    ElMessage.warning('该方案生成失败，无法查看详情')
    return
  }
  
  // 历史方案是只读的，不应该修改当前任务状态
  // 使用独立的 viewingHistoryItem 来存储历史方案数据
  viewingHistoryItem.value = {
    implementation_path: historyItem.implementation_path,
    papers_analysis: historyItem.papers_analysis || [],
    timings: historyItem.timings || null
  }
  
  // 设置对话框模式为显示历史方案（只读）
  dialogMode.value = 'history'
  showHistoryDialog.value = false
  showPathDialog.value = true
  
  // 不修改 currentTask，确保当前任务状态不受影响
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  try {
    // SQLite 返回的时间格式可能是 "YYYY-MM-DD HH:MM:SS"（UTC时间）
    // 需要将其解析为 UTC 时间，然后转换为本地时间
    let date
    if (typeof dateStr === 'string' && dateStr.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)) {
      // 格式为 "YYYY-MM-DD HH:MM:SS"，假设这是 UTC 时间
      date = new Date(dateStr + ' UTC')
    } else {
      // 其他格式，使用标准解析
      date = new Date(dateStr)
    }
    
    // 如果解析失败，返回原字符串
    if (isNaN(date.getTime())) {
      return dateStr
    }
    
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    })
  } catch (e) {
    return dateStr
  }
}

// 加载所有实现路径历史
const loadAllImplementationPathHistory = async () => {
  allHistoryLoading.value = true
  allHistoryError.value = null
  allHistoryPathList.value = []
  
  try {
    const response = await api.get('/papers/implementation-path-history', {
      params: {
        page: allHistoryPage.value,
        page_size: allHistoryPageSize.value
      }
    })
    allHistoryPathList.value = response.data.items || []
    allHistoryTotal.value = response.data.total || 0
  } catch (error) {
    allHistoryError.value = error.response?.data?.detail || error.message || '加载所有历史方案失败'
    ElMessage.error(allHistoryError.value)
  } finally {
    allHistoryLoading.value = false
  }
}
</script>

<style scoped>
.smart-match {
  min-height: calc(100vh - 60px);
}

/* Hero Section */
.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 80px 0;
  text-align: center;
}

.hero-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

.hero-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: bold;
  margin-bottom: 20px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 1.2rem;
  margin-bottom: 40px;
  opacity: 0.9;
  line-height: 1.6;
}

.search-container {
  margin-top: 40px;
  text-align: left;
}

.search-textarea {
  margin-bottom: 24px;
}

.search-textarea :deep(.el-textarea__inner) {
  font-size: 16px;
  line-height: 1.6;
  padding: 16px;
  border-radius: 8px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.95);
  color: #333;
  transition: all 0.3s;
}

.search-textarea :deep(.el-textarea__inner):focus {
  border-color: rgba(255, 255, 255, 0.8);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.2);
}

.mode-selector {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.mode-selector :deep(.el-radio-group) {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 4px;
}

.mode-selector :deep(.el-radio-button__inner) {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.8);
  padding: 12px 24px;
}

.mode-selector :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #fff;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.match-button {
  width: 100%;
  height: 56px;
  font-size: 18px;
  font-weight: 600;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s;
}

.match-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

/* 结果区域 */
.results-section {
  padding: 60px 0;
  background: #f5f5f5;
  min-height: 400px;
}

/* 结果卡片包装器 - 添加边框和间距 */
.result-card-wrapper {
  margin-bottom: 32px;
  padding: 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  transition: all 0.3s;
  box-shadow: 0 2px 12px rgba(102, 126, 234, 0.25);
  border: 1px solid rgba(102, 126, 234, 0.3);
}

.result-card-wrapper:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
  border-color: rgba(102, 126, 234, 0.5);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 这些样式在.results-header中已重新定义 */

.paper-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  min-height: 280px;
  transition: all 0.3s;
  position: relative;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.card.selected {
  border: 2px solid #409eff;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.2);
}

.card-checkbox-wrapper {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
}

.paper-checkbox {
  width: auto;
}

.paper-checkbox :deep(.el-checkbox__label) {
  display: none;
}

.paper-checkbox :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #409eff;
  border-color: #409eff;
}

.paper-checkbox :deep(.el-checkbox__inner) {
  width: 20px;
  height: 20px;
  border: 2px solid #409eff;
  border-radius: 4px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.implementation-path-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}

.path-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.path-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #303133;
  font-size: 18px;
}

.path-section ul {
  margin: 10px 0;
  padding-left: 20px;
}

.path-section li {
  margin: 5px 0;
  line-height: 1.6;
}

/* 实现路径 - 阶段目标与关键任务样式 */
.phase-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.phase-objectives {
  margin-top: 10px;
}

.phase-objectives-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.phase-pill-tag {
  border-radius: 16px;
  padding: 4px 10px;
  font-size: 13px;
  line-height: 1.4;
}

.phase-key-tasks {
  margin-top: 12px;
}

.phase-task-list {
  list-style: none;
  padding: 0;
  margin: 4px 0 0 0;
}

.phase-task-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  margin-bottom: 6px;
}

.phase-task-index {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.phase-task-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.tech-selection {
  margin-top: 10px;
}

.risk-assessment {
  margin-top: 10px;
}

.path-loading {
  padding: 40px;
}

.path-error {
  padding: 40px;
  text-align: center;
}

.card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-header {
  margin-bottom: 16px;
  padding-right: 40px;
}

.paper-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word; /* 允许在单词内换行，处理长文本 */
  word-wrap: break-word; /* 兼容性：旧版浏览器 */
  overflow-wrap: break-word; /* 标准属性 */
}

.card-body {
  flex: 1;
  margin-bottom: 16px;
}

.summary-content {
  color: #4b5563;
  min-height: 80px;
  font-size: 14px;
  line-height: 1.8;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word; /* 允许在单词内换行，处理长文本 */
  word-wrap: break-word; /* 兼容性：旧版浏览器 */
  overflow-wrap: break-word; /* 标准属性 */
}

.summary-content :deep(.highlight) {
  background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(146, 64, 14, 0.1);
}

.confidence-section {
  margin: 16px 0;
  padding: 14px;
  background: #f8fafc;
  border-radius: 10px;
}

.score-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #64748b;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #f1f5f9;
  border-radius: 6px;
  transition: all 0.2s;
}

.meta-item:hover {
  background: #e2e8f0;
}

.meta-item .el-icon {
  font-size: 13px;
  color: #64748b;
}

/* 推荐理由样式 */
.reason-section {
  margin: 16px 0;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 10px;
  border-left: 4px solid #3b82f6;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
}

.reason-label {
  font-size: 13px;
  font-weight: 600;
  color: #3b82f6;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.reason-text {
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
  word-break: break-word; /* 允许在单词内换行，处理长文本 */
  word-wrap: break-word; /* 兼容性：旧版浏览器 */
  overflow-wrap: break-word; /* 标准属性 */
}

/* 分数头部样式 */
.score-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.score-header span {
  font-size: 13px;
  color: #666;
}

.card-footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  gap: 8px;
  justify-content: flex-start;
}

.card-footer .el-button {
  flex: 1;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }

  .hero-subtitle {
    font-size: 1rem;
  }

  .results-title {
    font-size: 2rem;
  }

  .search-textarea :deep(.el-textarea__inner) {
    font-size: 14px;
  }

  .mode-selector :deep(.el-radio-button__inner) {
    padding: 10px 16px;
    font-size: 14px;
  }
}

/* 论文选择和实现路径相关样式 */
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 20px;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
}

.results-header > div:first-child {
  flex: 1;
}

.results-title {
  color: #fff;
  margin-bottom: 8px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.results-subtitle {
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: none;
  font-weight: 600;
}

.action-buttons .el-button--success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.action-buttons .el-button--success:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
}

.paper-card.selected {
  border: 2px solid #409eff;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.2);
}

/* 实现路径对话框样式 */
.implementation-path-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}

.path-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.path-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #303133;
  font-size: 18px;
}

.path-section ul {
  margin: 10px 0;
  padding-left: 20px;
}

.path-section li {
  margin: 5px 0;
  line-height: 1.6;
}

.tech-selection {
  margin-top: 10px;
}

.risk-assessment {
  margin-top: 10px;
}

.path-loading {
  padding: 40px;
}

.path-error {
  padding: 40px;
  text-align: center;
}

/* 历史方案对话框样式 */
.history-path-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}

.history-loading,
.history-error,
.history-empty {
  padding: 40px;
  text-align: center;
}

.history-list {
  padding: 20px 0;
}

.history-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.history-item-header h4 {
  margin: 0;
  color: #303133;
}

.history-item-content {
  color: #606266;
  font-size: 14px;
}

.history-item-content p {
  margin: 8px 0;
  line-height: 1.6;
}

/* 论文分析详情样式 */
.paper-analysis-content {
  padding: 10px 0;
}

.analysis-item {
  margin-top: 20px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #409eff;
}

.analysis-item h4 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 16px;
}

.analysis-item p {
  margin: 5px 0;
  line-height: 1.6;
  color: #606266;
}

.analysis-item ul {
  margin: 5px 0;
  padding-left: 20px;
}

.analysis-item li {
  margin: 5px 0;
  line-height: 1.6;
}

/* 所有历史方案对话框样式 */
.all-history-path-dialog :deep(.el-dialog__body) {
  max-height: 75vh;
  overflow-y: auto;
}

.all-history-list {
  padding: 20px 0;
}
</style>

