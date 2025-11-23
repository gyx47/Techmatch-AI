# 前后端接口对接文档

## 一、数据库表结构

### 1. users 表
```sql
users (user_id, username, email, password_hash, role, created_at)
```
- `user_id`: 主键，自增
- `username`: 用户名，唯一
- `email`: 邮箱，唯一
- `password_hash`: 密码哈希值
- `role`: 用户角色，'researcher'（科研人员）| 'enterprise'（企业用户）
- `created_at`: 创建时间

### 2. achievements 表
```sql
achievements (achievement_id, user_id, data_source, title, description, 
              technical_field, authors, application, keywords, 
              contact_name, contact_info, source_url)
```
- `achievement_id`: 主键，自增
- `user_id`: 外键，关联users表（如果是用户发布）
- `data_source`: 数据来源，'用户发布' | '系统采集'
- `title`: 成果标题
- `description`: 成果描述
- `technical_field`: 技术领域
- `authors`: 作者（可选）
- `application`: 应用场景
- `keywords`: 关键词列表（JSON数组或TEXT）
- `contact_name`: 联系人姓名（用户发布时必填）
- `contact_info`: 联系方式（JSON格式：`{"phone": "xxx", "email": "xxx"}`）
- `source_url`: 来源URL（系统采集时使用）

### 3. needs 表
```sql
needs (need_id, user_id, data_source, title, description, industry_field, 
       keywords, contact_org, contact_name, contact_info, source_url)
```
- `need_id`: 主键，自增
- `user_id`: 外键，关联users表（如果是用户发布）
- `data_source`: 数据来源，'用户发布' | '系统采集'
- `title`: 需求标题
- `description`: 需求描述
- `industry_field`: 行业领域
- `keywords`: 关键词列表（JSON数组或TEXT）
- `contact_org`: 企业/机构名称
- `contact_name`: 联系人姓名（用户发布时必填）
- `contact_info`: 联系方式（JSON格式：`{"phone": "xxx", "email": "xxx"}`）
- `source_url`: 来源URL（系统采集时使用）

### 4. match_history 表
```sql
match_history (history_id, user_id, search_desc, match_mode, 
               result_count, match_time)
```
- `history_id`: 主键，自增
- `user_id`: 外键，关联users表
- `search_desc`: 搜索描述（用户输入的匹配内容）
- `match_mode`: 匹配模式，'enterprise'（企业找成果）| 'researcher'（专家找需求）
- `result_count`: 匹配结果数量
- `match_time`: 匹配时间

### 5. match_results 表
```sql
match_results (result_id, history_id, source_id, source_type, 
               match_score, title_snapshot, abstract_snapshot)
```
- `result_id`: 主键，自增
- `history_id`: 外键，关联match_history表
- `source_id`: 源数据ID（关联achievements.achievement_id或needs.need_id）
- `source_type`: 源数据类型，'achievement'（成果）| 'need'（需求）
- `match_score`: 匹配度分数（0-100）
- `title_snapshot`: 标题快照（匹配时的标题）
- `abstract_snapshot`: 摘要快照（匹配时的摘要）

### 6. collaboration_plans 表
```sql
collaboration_plans (plan_id, result_id, plan_title, collab_mode, 
                     ai_analysis, feasibility_score, business_value, 
                     industry_score, total_score, contact_snapshot)
```
- `plan_id`: 主键，自增
- `result_id`: 外键，关联match_results表
- `plan_title`: 合作方案标题
- `collab_mode`: 合作模式
- `ai_analysis`: AI匹配分析文本
- `feasibility_score`: 可行性评分（技术匹配度）
- `business_value`: 商业价值评分（需求匹配度）
- `industry_score`: 行业匹配度评分（应用匹配度）
- `total_score`: 总体匹配度评分
- `contact_snapshot`: 联系方式快照（JSON格式，保存查看时的联系方式）

### 7. ai_conversations 表
```sql
ai_conversations (conversation_id, user_id, session_id, sender, 
                  message, created_at)
```
- `conversation_id`: 主键，自增
- `user_id`: 外键，关联users表
- `session_id`: 会话ID
- `sender`: 发送者，'user'（用户）| 'ai'（AI）
- `message`: 消息内容
- `created_at`: 创建时间

### 8. achievements_vector 表（向量数据库）
```sql
achievements_vector (achievement_vector_id, embeddings, document, metadata)
```
- 用于存储成果的向量化表示，用于相似度搜索
- `achievement_vector_id`: 对应achievements.achievement_id

### 9. needs_vector 表（向量数据库）
```sql
needs_vector (need_vector_id, embeddings, document, metadata)
```
- 用于存储需求的向量化表示，用于相似度搜索
- `need_vector_id`: 对应needs.need_id

---

## 二、前端页面与接口对应关系

### 页面结构说明

#### 1. App.vue（主应用框架）
- **功能**：提供顶部导航栏、用户状态管理、路由容器
- **导航菜单**：首页、资源大厅、发布中心、智能匹配、个人中心
- **用户区域**：未登录显示"登录/注册"按钮，已登录显示用户下拉菜单

#### 2. Home.vue（首页）
- **功能**：平台介绍、核心功能展示、快速导航
- **不需要接口**：纯展示页面

#### 3. Login.vue（登录页面）
- **功能**：用户登录、快速体验（mockLogin）
- **对应接口**：用户登录接口

#### 4. Register.vue（注册页面）
- **功能**：用户注册、角色选择（科研人员/企业用户）
- **对应接口**：用户注册接口

#### 5. Dashboard.vue（资源大厅）
- **功能**：浏览成果和需求列表、查看详情
- **标签页**："找成果"、"找需求"
- **对应接口**：获取成果列表、获取需求列表、获取成果详情、获取需求详情

#### 6. PublishCenter.vue（发布中心）
- **功能**：发布成果（科研人员）或发布需求（企业用户）
- **角色判断**：根据用户角色显示不同表单
- **对应接口**：发布成果接口、发布需求接口、AI辅助润色接口（可选）

#### 7. SmartMatch.vue（智能匹配）
- **功能**：输入搜索描述、选择匹配模式、执行匹配、显示匹配结果
- **对应接口**：执行智能匹配接口、获取匹配历史列表、根据历史ID获取匹配结果

#### 8. MatchProposal.vue（合作方案详情）
- **功能**：显示合作方案详细信息、AI匹配分析、联系方式
- **对应接口**：获取或创建合作方案接口

#### 9. UserProfile.vue（个人中心）
- **功能**：
  - 标签页1：我的发布（成果和需求列表，支持编辑、删除）
  - 标签页2：匹配历史（历史匹配记录，支持查看结果）
  - 标签页3：账号设置（修改密码）
- **对应接口**：获取我的发布列表、编辑成果、编辑需求、删除成果、删除需求、获取匹配历史列表、修改密码

---

## 三、后端接口需求清单

### 1. 用户认证接口

#### 1.1 用户注册
**接口路径**：`POST /api/auth/register`  
**对应页面**：Register.vue  
**功能说明**：用户注册新账号，注册时需要选择角色（科研人员或企业用户）

**请求参数**：
```json
{
  "username": "string",           // 必填，用户名，3-20个字符
  "email": "string",              // 必填，邮箱地址，需验证格式
  "password": "string",           // 必填，密码，至少8个字符
  "role": "researcher" | "enterprise"  // 必填，用户角色
}
```

**响应数据**：
```json
{
  "access_token": "string",       // JWT访问令牌
  "token_type": "bearer",         // 令牌类型
  "user": {
    "user_id": 1,
    "username": "string",
    "email": "string",
    "role": "researcher" | "enterprise"  // 必须返回角色字段
  }
}
```

---

#### 1.2 用户登录
**接口路径**：`POST /api/auth/login`  
**对应页面**：Login.vue  
**功能说明**：用户使用用户名和密码登录

**请求参数**：
```json
{
  "username": "string",    // 必填，用户名
  "password": "string"      // 必填，密码
}
```

**响应数据**：
```json
{
  "access_token": "string",  // JWT访问令牌
  "token_type": "bearer"    // 令牌类型
}
```

---

#### 1.3 获取当前用户信息
**接口路径**：`GET /api/auth/me`  
**对应页面**：App.vue（导航栏显示用户信息）、UserProfile.vue（个人中心）  
**功能说明**：获取当前登录用户的详细信息，用于显示用户名、角色等信息

**请求头**：
```
Authorization: Bearer {access_token}
```

**响应数据**：
```json
{
  "user_id": 1,
  "username": "string",
  "email": "string",
  "role": "researcher" | "enterprise",  // 重要：必须返回角色字段
  "created_at": "2024-01-01T00:00:00"
}
```

---

### 2. 资源大厅接口（Dashboard.vue）

#### 2.1 获取成果列表
**接口路径**：`GET /api/achievements`  
**对应页面**：Dashboard.vue（"找成果"标签页）  
**功能说明**：分页获取成果列表，支持按技术领域和数据来源筛选，用于在资源大厅展示成果卡片列表

**查询参数**：
- `page`: int，页码，默认1
- `page_size`: int，每页数量，默认10
- `technical_field`: string，可选，技术领域筛选（如"人工智能/机器学习"）
- `data_source`: string，可选，数据来源筛选（'用户发布' | '系统采集'）
- `keyword`: string，可选，关键词搜索（在标题、描述、关键词中搜索）

**响应数据**：
```json
{
  "total": 100,
  "page": 1,
  "page_size": 10,
  "items": [
    {
      "achievement_id": 1,
      "title": "string",                    // 成果标题
      "description": "string",              // 成果描述（摘要，用于卡片显示）
      "technical_field": "string",         // 技术领域
      "authors": "string",                 // 作者（可选）
      "application": "string",             // 应用场景
      "keywords": ["string"],              // 关键词数组
      "data_source": "用户发布" | "系统采集",
      "contact_name": "string",            // 如果是用户发布且用户已登录，返回联系人
      "contact_info": {                    // 如果是用户发布且用户已登录，返回联系方式
        "phone": "string",
        "email": "string"
      },
      "source_url": "string",              // 如果是系统采集，返回来源URL
      "created_at": "2024-01-20T00:00:00" // 发布时间
    }
  ]
}
```

**权限说明**：
- 无需登录即可访问
- 登录用户可以看到联系方式，未登录用户看不到contact_name和contact_info

---

#### 2.2 获取需求列表
**接口路径**：`GET /api/needs`  
**对应页面**：Dashboard.vue（"找需求"标签页）  
**功能说明**：分页获取需求列表，支持按行业领域和数据来源筛选，用于在资源大厅展示需求卡片列表

**查询参数**：
- `page`: int，页码，默认1
- `page_size`: int，每页数量，默认10
- `industry_field`: string，可选，行业领域筛选（如"互联网/电商"）
- `data_source`: string，可选，数据来源筛选（'用户发布' | '系统采集'）
- `keyword`: string，可选，关键词搜索

**响应数据**：
```json
{
  "total": 100,
  "page": 1,
  "page_size": 10,
  "items": [
    {
      "need_id": 101,
      "title": "string",                    // 需求标题
      "description": "string",              // 需求描述（用于卡片显示）
      "industry_field": "string",          // 行业领域
      "keywords": ["string"],              // 关键词数组
      "contact_org": "string",             // 企业/机构名称
      "data_source": "用户发布" | "系统采集",
      "contact_name": "string",            // 如果是用户发布且用户已登录，返回联系人
      "contact_info": {                    // 如果是用户发布且用户已登录，返回联系方式
        "phone": "string",
        "email": "string"
      },
      "source_url": "string",              // 如果是系统采集，返回来源URL
      "created_at": "2024-01-20T00:00:00" // 发布时间
    }
  ]
}
```

**权限说明**：
- 无需登录即可访问
- 登录用户可以看到联系方式

---

#### 2.3 获取成果详情
**接口路径**：`GET /api/achievements/{achievement_id}`  
**对应页面**：Dashboard.vue（点击"查看详情"按钮打开的抽屉）  
**功能说明**：获取单个成果的详细信息，用于在抽屉中展示完整信息

**路径参数**：
- `achievement_id`: int，成果ID

**请求头**（可选）：
```
Authorization: Bearer {access_token}  // 登录用户可查看联系方式
```

**响应数据**：
```json
{
  "achievement_id": 1,
  "title": "string",
  "description": "string",              // 完整描述
  "technical_field": "string",
  "authors": "string",
  "application": "string",
  "keywords": ["string"],
  "data_source": "用户发布" | "系统采集",
  "contact_name": "string",             // 需要权限控制
  "contact_info": {                     // 需要权限控制
    "phone": "string",
    "email": "string"
  },
  "source_url": "string",               // 系统采集时返回
  "created_at": "2024-01-20T00:00:00"
}
```

**权限说明**：
- 基本信息：所有人可见
- 联系方式：仅登录用户可见

---

#### 2.4 获取需求详情
**接口路径**：`GET /api/needs/{need_id}`  
**对应页面**：Dashboard.vue（点击"查看详情"按钮打开的抽屉）  
**功能说明**：获取单个需求的详细信息，用于在抽屉中展示完整信息

**路径参数**：
- `need_id`: int，需求ID

**请求头**（可选）：
```
Authorization: Bearer {access_token}  // 登录用户可查看联系方式
```

**响应数据**：
```json
{
  "need_id": 101,
  "title": "string",
  "description": "string",              // 完整描述
  "industry_field": "string",
  "keywords": ["string"],
  "contact_org": "string",              // 企业/机构名称
  "data_source": "用户发布" | "系统采集",
  "contact_name": "string",             // 需要权限控制
  "contact_info": {                     // 需要权限控制
    "phone": "string",
    "email": "string"
  },
  "source_url": "string",               // 系统采集时返回
  "created_at": "2024-01-20T00:00:00"
}
```

**权限说明**：
- 基本信息：所有人可见
- 联系方式：仅登录用户可见

---

### 3. 发布中心接口（PublishCenter.vue）

#### 3.1 发布成果（科研人员）
**接口路径**：`POST /api/achievements`  
**对应页面**：PublishCenter.vue（当用户角色为'researcher'时显示）  
**功能说明**：科研人员发布科研成果，表单包含成果名称、技术领域、成果简介、应用场景、联系人、电话

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "title": "string",                    // 必填，成果名称
  "description": "string",              // 必填，成果简介（详细描述）
  "technical_field": "string",         // 必填，技术领域
  "authors": "string",                  // 可选，作者
  "application": "string",              // 必填，应用场景
  "keywords": ["string"],              // 可选，关键词数组
  "contact_name": "string",            // 必填，联系人姓名
  "contact_info": {                    // 必填，联系方式
    "phone": "string",                 // 必填，联系电话
    "email": "string"                  // 必填，联系邮箱
  }
}
```

**响应数据**：
```json
{
  "achievement_id": 1,
  "message": "发布成功"
}
```

**功能要求**：
- 验证用户角色必须是'researcher'（科研人员）
- 将contact_info转换为JSON格式存储到数据库
- 设置data_source为'用户发布'
- 保存到achievements表，user_id为当前用户ID
- 同时需要更新achievements_vector表（向量化存储，用于后续匹配）

---

#### 3.2 发布需求（企业用户）
**接口路径**：`POST /api/needs`  
**对应页面**：PublishCenter.vue（当用户角色为'enterprise'时显示）  
**功能说明**：企业用户发布技术需求，表单包含需求标题、行业领域、需求详细描述、企业名称、联系人、电话

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "title": "string",                    // 必填，需求标题
  "description": "string",              // 必填，需求详细描述
  "industry_field": "string",         // 必填，行业领域
  "keywords": ["string"],              // 可选，关键词数组
  "contact_org": "string",             // 必填，企业名称
  "contact_name": "string",            // 必填，联系人姓名
  "contact_info": {                    // 必填，联系方式
    "phone": "string",                 // 必填，联系电话
    "email": "string"                  // 必填，联系邮箱
  }
}
```

**响应数据**：
```json
{
  "need_id": 101,
  "message": "发布成功"
}
```

**功能要求**：
- 验证用户角色必须是'enterprise'（企业用户）
- 将contact_info转换为JSON格式存储
- 设置data_source为'用户发布'
- 保存到needs表，user_id为当前用户ID
- 同时需要更新needs_vector表（向量化存储，用于后续匹配）

---

#### 3.3 AI辅助润色（可选功能）
**接口路径**：`POST /api/ai/polish`  
**对应页面**：PublishCenter.vue（成果简介和需求描述输入框下方的"AI 辅助润色"按钮）  
**功能说明**：使用AI对成果简介或需求描述进行润色优化，提升文本质量

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "text": "string",                    // 必填，需要润色的文本
  "type": "achievement" | "need"       // 必填，文本类型
}
```

**响应数据**：
```json
{
  "polished_text": "string"            // 润色后的文本
}
```

**功能要求**：
- 调用AI模型对文本进行优化
- 保持原意，提升表达质量
- 前端点击按钮后显示"AI正在优化您的文本..."提示

---

### 4. 智能匹配接口（SmartMatch.vue）

#### 4.1 执行智能匹配
**接口路径**：`POST /api/match/execute`  
**对应页面**：SmartMatch.vue（点击"开始智能匹配"按钮）  
**功能说明**：根据用户输入的搜索描述和匹配模式，使用向量相似度搜索匹配最相关的成果或需求，返回匹配结果列表

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "search_desc": "string",                    // 必填，搜索描述（用户输入的匹配内容）
  "match_mode": "enterprise" | "researcher"  // 必填，匹配模式
}
```

**响应数据**：
```json
{
  "history_id": 1,                           // 匹配历史ID
  "result_count": 5,                         // 匹配结果数量
  "results": [
    {
      "result_id": 1,                        // 匹配结果ID（用于前端显示和后续查看合作方案）
      "source_id": 101,                       // 源数据ID（achievement_id或need_id）
      "source_type": "achievement" | "need",  // 源数据类型
      "match_score": 95,                      // 匹配度分数（0-100）
      "title_snapshot": "string",            // 标题快照
      "abstract_snapshot": "string",         // 摘要快照
      "source_data": {                       // 完整的源数据（用于前端显示）
        "id": 101,
        "title": "string",
        "summary": "string",
        "type": "成果" | "需求",
        "field": "string",
        "company": "string",                  // 如果是需求
        "keywords": ["string"]
      }
    }
  ]
}
```

**功能要求**：
1. **向量搜索**：
   - 将search_desc进行向量化
   - 根据match_mode选择搜索目标：
     - enterprise模式：在achievements_vector中搜索（企业找成果）
     - researcher模式：在needs_vector中搜索（专家找需求）
   - 计算相似度，返回top N个结果（建议5-10个）

2. **创建匹配历史**：
   - 在match_history表中创建记录
   - 记录search_desc、match_mode、result_count

3. **保存匹配结果**：
   - 在match_results表中为每个结果创建记录
   - 保存source_id、source_type、match_score
   - 保存title_snapshot和abstract_snapshot（快照，防止源数据被修改）

4. **返回数据**：
   - 返回完整的source_data，方便前端直接显示
   - 按match_score降序排列

---

#### 4.2 获取匹配历史列表
**接口路径**：`GET /api/match/history`  
**对应页面**：UserProfile.vue（"匹配历史"标签页）  
**功能说明**：获取当前用户的匹配历史记录列表，用于在个人中心展示历史匹配记录表格

**请求头**：
```
Authorization: Bearer {access_token}
```

**查询参数**：
- `page`: int，页码，默认1
- `page_size`: int，每页数量，默认20

**响应数据**：
```json
{
  "total": 50,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "history_id": 1,                       // 历史记录ID
      "search_desc": "string",               // 搜索描述（用于表格显示，前端会截取）
      "match_mode": "enterprise" | "researcher",
      "match_type": "找成果" | "找需求",      // 前端显示用，根据match_mode转换
      "result_count": 5,                     // 匹配结果数量
      "match_time": "2024-01-15T14:30:25"    // 匹配时间
    }
  ]
}
```

**功能要求**：
- 根据当前用户ID查询match_history表
- 只返回当前用户的匹配历史
- 按match_time降序排列（最新的在前）
- 支持分页

---

#### 4.3 根据历史ID获取匹配结果
**接口路径**：`GET /api/match/history/{history_id}/results`  
**对应页面**：SmartMatch.vue（从UserProfile.vue的"匹配历史"点击"查看结果"跳转过来）  
**功能说明**：根据匹配历史ID，获取该次匹配的所有结果详情，用于在智能匹配页面恢复显示之前的匹配结果

**路径参数**：
- `history_id`: int，匹配历史ID

**请求头**：
```
Authorization: Bearer {access_token}
```

**响应数据**：
```json
{
  "history": {                               // 匹配历史信息
    "history_id": 1,
    "search_desc": "string",
    "match_mode": "enterprise" | "researcher",
    "result_count": 5,
    "match_time": "2024-01-15T14:30:25"
  },
  "results": [                               // 匹配结果列表
    {
      "result_id": 1,
      "source_id": 101,
      "source_type": "achievement" | "need",
      "match_score": 95,
      "title_snapshot": "string",            // 匹配时的标题快照
      "abstract_snapshot": "string",         // 匹配时的摘要快照
      "source_data": {                       // 当前源数据（可能已更新）
        "id": 101,
        "title": "string",
        "summary": "string",
        "type": "成果" | "需求",
        "field": "string",
        "keywords": ["string"]
      }
    }
  ]
}
```

**功能要求**：
- 验证history_id属于当前用户
- 查询match_history表获取历史信息
- 查询match_results表获取所有匹配结果
- 根据source_id和source_type，查询最新的源数据
- 返回快照数据和当前源数据（前端可以对比显示）

---

### 5. 合作方案接口（MatchProposal.vue）

#### 5.1 获取或创建合作方案
**接口路径**：`GET /api/collaboration-plans/{result_id}`  
**对应页面**：MatchProposal.vue（从SmartMatch.vue点击"查看合作方案"按钮跳转）  
**功能说明**：根据匹配结果ID，获取或创建合作方案详情。如果方案已存在则直接返回，如果不存在则生成新方案（调用AI生成分析、计算评分）

**路径参数**：
- `result_id`: int，匹配结果ID（来自match_results表）

**请求头**：
```
Authorization: Bearer {access_token}
```

**响应数据**：
```json
{
  "plan_id": 1,                              // 合作方案ID
  "result_id": 1,                            // 匹配结果ID
  "plan_title": "string",                    // 合作方案标题
  "collab_mode": "string",                   // 合作模式
  "ai_analysis": "string",                   // AI匹配分析文本（详细分析，用于左侧AI分析卡片）
  "description": "string",                   // 详细描述（用于左侧详细描述区域）
  "field": "string",                         // 技术领域（用于技术指标）
  "application": "string",                   // 应用场景（用于技术指标）
  "maturity": "string",                      // 技术成熟度（用于技术指标）
  "duration": "string",                      // 预期周期（用于技术指标）
  "advantages": "string",                    // 核心优势（用于技术指标）
  "feasibility_score": 95,                   // 可行性评分（技术匹配度，0-100）
  "business_value": 92,                      // 商业价值评分（需求匹配度，0-100）
  "industry_score": 90,                      // 行业匹配度评分（应用匹配度，0-100）
  "total_score": 95,                         // 总体匹配度评分（0-100，用于右侧匹配度仪表盘）
  "contact_snapshot": {                      // 联系方式快照（用于右侧对接信息卡片）
    "name": "string",
    "phone": "string",
    "email": "string",
    "organization": "string"
  },
  "source_data": {                           // 关联的成果或需求完整数据
    "id": 101,
    "title": "string",
    "description": "string",
    "field": "string",
    "application": "string",                 // 如果是成果
    "industry_field": "string",              // 如果是需求
    "company": "string"                      // 如果是需求
  }
}
```

**功能要求**：
1. **检查方案是否存在**：
   - 查询collaboration_plans表，根据result_id查找
   - 如果存在，直接返回

2. **如果不存在，生成新方案**：
   - 根据result_id查询match_results表
   - 根据source_id和source_type查询完整的成果或需求数据
   - 调用AI生成合作方案分析（ai_analysis）
   - 计算各项评分（feasibility_score、business_value、industry_score、total_score）
   - 保存联系方式快照（contact_snapshot）
   - 创建collaboration_plans记录
   - 返回完整的合作方案

3. **权限控制**：
   - 验证result_id对应的history_id属于当前用户

---

#### 5.2 保存合作方案（查看时自动保存）
**接口路径**：`POST /api/collaboration-plans`  
**对应页面**：MatchProposal.vue（查看方案时自动调用）  
**功能说明**：保存合作方案（通常由5.1接口自动调用，前端也可手动调用）

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "result_id": 1,                            // 必填，匹配结果ID
  "plan_title": "string",                    // 必填，合作方案标题
  "collab_mode": "string",                   // 可选，合作模式
  "ai_analysis": "string",                   // 必填，AI匹配分析
  "feasibility_score": 95,                   // 必填，可行性评分
  "business_value": 92,                      // 必填，商业价值评分
  "industry_score": 90,                      // 必填，行业匹配度评分
  "total_score": 95,                         // 必填，总体评分
  "contact_snapshot": {                      // 必填，联系方式快照
    "name": "string",
    "phone": "string",
    "email": "string",
    "organization": "string"
  }
}
```

**响应数据**：
```json
{
  "plan_id": 1,
  "message": "保存成功"
}
```

**功能要求**：
- 验证result_id属于当前用户
- 将contact_snapshot转换为JSON格式存储
- 保存到collaboration_plans表
- 如果已存在相同result_id的方案，则更新

---

### 6. 个人中心接口（UserProfile.vue）

#### 6.1 获取我的发布列表
**接口路径**：`GET /api/user/publishments`  
**对应页面**：UserProfile.vue（"我的发布"标签页）  
**功能说明**：获取当前用户发布的所有成果和需求列表，用于在个人中心展示表格（支持编辑、删除操作）

**请求头**：
```
Authorization: Bearer {access_token}
```

**查询参数**：
- `type`: string，可选，筛选类型（'achievement' | 'need'），不传则返回全部

**响应数据**：
```json
{
  "achievements": [                          // 成果列表
    {
      "achievement_id": 1,
      "title": "string",
      "technical_field": "string",
      "type": "成果",                         // 前端显示用
      "created_at": "2024-01-20T00:00:00"
    }
  ],
  "needs": [                                 // 需求列表
    {
      "need_id": 101,
      "title": "string",
      "industry_field": "string",
      "type": "需求",                         // 前端显示用
      "created_at": "2024-01-20T00:00:00"
    }
  ]
}
```

**功能要求**：
- 根据当前用户ID查询achievements表和needs表
- 只返回data_source='用户发布'的记录
- 如果指定type，只返回对应类型的数据
- 按created_at降序排列

---

#### 6.2 编辑成果
**接口路径**：`PUT /api/achievements/{achievement_id}`  
**对应页面**：UserProfile.vue（"我的发布"标签页，点击"编辑"按钮）  
**功能说明**：编辑用户自己发布的成果

**路径参数**：
- `achievement_id`: int，成果ID

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "title": "string",
  "description": "string",
  "technical_field": "string",
  "authors": "string",
  "application": "string",
  "keywords": ["string"],
  "contact_name": "string",
  "contact_info": {
    "phone": "string",
    "email": "string"
  }
}
```
（与发布成果接口相同）

**响应数据**：
```json
{
  "message": "更新成功"
}
```

**功能要求**：
- 验证achievement_id属于当前用户
- 验证data_source='用户发布'（不能编辑系统采集的数据）
- 更新achievements表
- 同时更新achievements_vector表（向量数据）

---

#### 6.3 编辑需求
**接口路径**：`PUT /api/needs/{need_id}`  
**对应页面**：UserProfile.vue（"我的发布"标签页，点击"编辑"按钮）  
**功能说明**：编辑用户自己发布的需求

**路径参数**：
- `need_id`: int，需求ID

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "title": "string",
  "description": "string",
  "industry_field": "string",
  "keywords": ["string"],
  "contact_org": "string",
  "contact_name": "string",
  "contact_info": {
    "phone": "string",
    "email": "string"
  }
}
```
（与发布需求接口相同）

**响应数据**：
```json
{
  "message": "更新成功"
}
```

**功能要求**：
- 验证need_id属于当前用户
- 验证data_source='用户发布'
- 更新needs表
- 同时更新needs_vector表

---

#### 6.4 删除成果
**接口路径**：`DELETE /api/achievements/{achievement_id}`  
**对应页面**：UserProfile.vue（"我的发布"标签页，点击"删除"按钮）  
**功能说明**：删除用户自己发布的成果

**路径参数**：
- `achievement_id`: int，成果ID

**请求头**：
```
Authorization: Bearer {access_token}
```

**响应数据**：
```json
{
  "message": "删除成功"
}
```

**功能要求**：
- 验证achievement_id属于当前用户
- 验证data_source='用户发布'
- 删除achievements表中的记录
- 同时删除achievements_vector表中的向量数据
- 注意：如果有match_results关联到此成果，需要考虑级联处理

---

#### 6.5 删除需求
**接口路径**：`DELETE /api/needs/{need_id}`  
**对应页面**：UserProfile.vue（"我的发布"标签页，点击"删除"按钮）  
**功能说明**：删除用户自己发布的需求

**路径参数**：
- `need_id`: int，需求ID

**请求头**：
```
Authorization: Bearer {access_token}
```

**响应数据**：
```json
{
  "message": "删除成功"
}
```

**功能要求**：
- 验证need_id属于当前用户
- 验证data_source='用户发布'
- 删除needs表中的记录
- 同时删除needs_vector表中的向量数据
- 注意：如果有match_results关联到此需求，需要考虑级联处理

---

#### 6.6 修改密码
**接口路径**：`PUT /api/user/password`  
**对应页面**：UserProfile.vue（"账号设置"标签页）  
**功能说明**：修改当前用户的登录密码

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求参数**：
```json
{
  "old_password": "string",    // 必填，当前密码
  "new_password": "string"     // 必填，新密码（至少8个字符）
}
```

**响应数据**：
```json
{
  "message": "修改成功"
}
```

**功能要求**：
- 验证old_password是否正确
- 验证new_password是否符合要求（至少8个字符）
- 对新密码进行哈希加密
- 更新users表中的password_hash

---

## 四、数据字段映射说明

### 前端字段 → 后端字段

#### 成果（Achievement）
- `id` → `achievement_id`
- `field` → `technical_field`
- `publish_time` → `created_at`
- `contact_name` → `contact_name`
- `contact_phone` → `contact_info.phone`
- `contact_email` → `contact_info.email`

#### 需求（Need）
- `id` → `need_id`
- `industry` → `industry_field`
- `company_name` → `contact_org`
- `publish_time` → `created_at`
- `contact_name` → `contact_name`
- `contact_phone` → `contact_info.phone`
- `contact_email` → `contact_info.email`

#### 匹配结果（Match Result）
- `id` → `result_id`
- `title` → `title_snapshot`
- `summary` → `abstract_snapshot`
- `matchScore` → `match_score`

#### 合作方案（Collaboration Plan）
- `id` → `plan_id`
- `title` → `plan_title`
- `aiAnalysis` → `ai_analysis`
- `matchScore` → `total_score`
- `techMatch` → `feasibility_score`
- `needMatch` → `business_value`
- `appMatch` → `industry_score`
- `contactInfo` → `contact_snapshot`

---

## 五、开发优先级建议

### 第一阶段（核心功能）
1. ✅ 用户认证（注册、登录、获取用户信息）- 已有，需确认role字段
2. ⭐ 资源大厅接口（获取成果和需求列表、详情）
3. ⭐ 发布中心接口（发布成果和需求）
4. ⭐ 智能匹配接口（执行匹配、保存历史、获取历史）

### 第二阶段（完善功能）
5. ⭐ 合作方案接口（获取/创建方案）
6. ⭐ 个人中心接口（我的发布、编辑、删除、修改密码）

### 第三阶段（优化功能）
7. AI辅助润色接口（可选）
8. 向量搜索优化（可选）
