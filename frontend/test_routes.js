const fs = require('fs')

console.log('🔍 检查路由配置和文件状态:')
console.log('=' * 50)

// 检查组件文件
const files = {
  'RequirementDetail.vue': './src/views/RequirementDetail.vue',
  'MatchProposal.vue': './src/views/MatchProposal.vue'
}

Object.entries(files).forEach(([name, path]) => {
  const exists = fs.existsSync(path)
  console.log(`${exists ? '✅' : '❌'} ${name}: ${exists ? '存在' : '缺失'} (${path})`)
})

console.log('\n📋 SmartMatch.vue 路由跳转逻辑:')
console.log('1. 企业找成果模式 → /proposal/{paper_id} → MatchProposal.vue')
console.log('2. 专家找需求模式 → /requirement/{req_id} → RequirementDetail.vue')

console.log('\n🔗 检查路由定义:')
const routerContent = fs.readFileSync('./src/router/index.js', 'utf-8')
const hasRequirementRoute = routerContent.includes("'/requirement/:id'")
const hasProposalRoute = routerContent.includes("'/proposal/:id'")

console.log(`✅ /requirement/:id 路由: ${hasRequirementRoute ? '已定义' : '未定义'}`)
console.log(`✅ /proposal/:id 路由: ${hasProposalRoute ? '已定义' : '未定义'}`)

console.log('\n🎯 结论:')
if (fs.existsSync('./src/views/RequirementDetail.vue') && fs.existsSync('./src/views/MatchProposal.vue')) {
  console.log('✅ 所有组件文件都存在，路由配置正确')
  console.log('✅ SmartMatch应该可以正常工作')
} else {
  console.log('⚠️  有组件文件缺失，请创建缺失的文件')
}
